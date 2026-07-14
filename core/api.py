from __future__ import annotations

import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from core.config import load_settings
from core.memory import MemoryStore
from core.obsidian_publisher import diagnose_vault_wikilinks
from core.operational_status import build_operational_status
from core.proposal_service import ProposalTrustService
from core.proposal_store import SQLiteProposalStore
from core.proposals import ValidationStatus, payload_to_dict
from core.release_runtime import DEMO_DB, DEMO_VAULT, demo_paths, seed_demo
from core.repository import SQLiteRepository


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"


class ApiError(BaseModel):
    error: str
    detail: str


class ProposalRejectRequest(BaseModel):
    reason: str


def create_app(
    *,
    project_root: Path | None = None,
    db_path: Path | None = None,
    vault_path: Path | None = None,
    auto_seed: bool = False,
) -> FastAPI:
    root = (project_root or PROJECT_ROOT).resolve()
    settings = load_settings(root)
    configured_db = settings.memory_db if _has_configured_db_env() else root / DEMO_DB
    configured_vault = settings.obsidian_vault_path if settings.obsidian_vault_path else root / DEMO_VAULT
    paths = demo_paths(root, db_path=db_path or configured_db, vault_path=vault_path or configured_vault)
    if auto_seed:
        seed_demo(root, db_path=paths.db_path, vault_path=paths.vault_path)

    app = FastAPI(
        title="Intelligence Hub API",
        version="0.4.0",
        description="Local-first Intelligence Hub release candidate API.",
    )
    app.state.project_root = root
    app.state.db_path = paths.db_path
    app.state.vault_path = paths.vault_path

    if DASHBOARD_DIR.exists():
        app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="static")

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content=ApiError(error="bad_request", detail=str(exc)).model_dump())

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(_: Request, exc: RuntimeError) -> JSONResponse:
        return JSONResponse(status_code=404, content=ApiError(error="not_found", detail=str(exc)).model_dump())

    @app.exception_handler(HTTPException)
    async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and {"error", "detail"} <= set(exc.detail):
            content = exc.detail
        else:
            content = ApiError(error="http_error", detail=str(exc.detail)).model_dump()
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=ApiError(error="validation_error", detail=str(exc.errors())).model_dump(),
        )

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        index = DASHBOARD_DIR / "index.html"
        if not index.exists():
            return "<h1>Intelligence Hub</h1><p>Dashboard assets are missing.</p>"
        return index.read_text(encoding="utf-8")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "platform": "intelligence_hub"}

    @app.get("/ready")
    def ready() -> dict[str, Any]:
        with _repository(app) as repository:
            return {
                "ready": True,
                "db_path": str(app.state.db_path),
                "entities": len(repository.list_entities()),
                "briefs": len(repository.list_briefs()),
                "insights": len(repository.list_insights()),
            }

    @app.get("/api/briefs")
    def briefs() -> list[dict[str, Any]]:
        with _repository(app) as repository:
            return [_brief(item) for item in repository.list_briefs()]

    @app.get("/api/briefs/{brief_id}")
    def brief(brief_id: str) -> dict[str, Any]:
        with _repository(app) as repository:
            for item in repository.list_briefs():
                if item.id == brief_id:
                    return _brief(item)
        raise HTTPException(status_code=404, detail=ApiError(error="not_found", detail="brief not found").model_dump())

    @app.get("/api/insights")
    def insights() -> list[dict[str, Any]]:
        with _repository(app) as repository:
            return [_dataclass(item) for item in repository.list_insights()]

    @app.get("/api/insights/{insight_id}")
    def insight(insight_id: str) -> dict[str, Any]:
        with _repository(app) as repository:
            for item in repository.list_insights():
                if item.id == insight_id:
                    return _dataclass(item)
        raise HTTPException(status_code=404, detail=ApiError(error="not_found", detail="insight not found").model_dump())

    @app.get("/api/entities")
    def entities() -> list[dict[str, Any]]:
        with _repository(app) as repository:
            return [_entity(item) for item in repository.list_entities()]

    @app.get("/api/entities/{entity_id}")
    def entity(entity_id: str) -> dict[str, Any]:
        with _repository(app) as repository:
            entities_by_id = {item.id: item for item in repository.list_entities()}
            item = entities_by_id.get(entity_id)
            if item is None:
                raise HTTPException(status_code=404, detail=ApiError(error="not_found", detail="entity not found").model_dump())
            relationships = [
                _dataclass(rel)
                for rel in repository.list_relationships()
                if rel.source_entity_id == item.id or rel.target_entity_id == item.id
            ]
            observations = [_dataclass(obs) for obs in repository.list_observations() if obs.entity_id == item.id]
            insights = [
                _dataclass(insight)
                for insight in repository.list_insights()
                if f"entity:{item.id}" in insight.related_entity_refs or f"source:{item.id}" in insight.related_entity_refs
            ]
            decisions = [
                _dataclass(decision)
                for decision in repository.list_decisions()
                if item.canonical_name.casefold() in decision.signal_id.casefold()
            ]
            data = _entity(item)
            data.update(
                relationships=relationships,
                observations=observations,
                insights=insights,
                decisions=decisions,
            )
            return data

    @app.get("/api/events")
    def events() -> list[dict[str, Any]]:
        with _repository(app) as repository:
            return [_dataclass(item) for item in repository.list_events()]

    @app.get("/api/decisions")
    def decisions() -> list[dict[str, Any]]:
        with _repository(app) as repository:
            return [_dataclass(item) for item in repository.list_decisions()]

    @app.get("/api/proposals")
    def proposals(status: ValidationStatus | None = None) -> list[dict[str, Any]]:
        with _repository(app) as repository:
            return [_proposal(item) for item in repository.list_proposals(status=status)]

    @app.get("/api/proposals/{proposal_id}")
    def proposal(proposal_id: str) -> dict[str, Any]:
        store = MemoryStore(app.state.db_path)
        try:
            return _proposal(SQLiteProposalStore.from_memory_store(store).get(proposal_id))
        finally:
            store.close()

    @app.post("/api/proposals/{proposal_id}/revalidate")
    def revalidate_proposal(proposal_id: str) -> dict[str, Any]:
        store = MemoryStore(app.state.db_path)
        try:
            proposals = SQLiteProposalStore.from_memory_store(store)
            result = ProposalTrustService(store=store, proposals=proposals).submit(proposals.get(proposal_id))
            return _proposal(result.proposal)
        finally:
            store.close()

    @app.post("/api/proposals/{proposal_id}/accept")
    def accept_proposal(proposal_id: str) -> dict[str, Any]:
        store = MemoryStore(app.state.db_path)
        try:
            result = ProposalTrustService(store=store).accept_needs_review(proposal_id)
            return _proposal(result.proposal)
        finally:
            store.close()

    @app.post("/api/proposals/{proposal_id}/reject")
    def reject_proposal(proposal_id: str, body: ProposalRejectRequest = Body(...)) -> dict[str, Any]:
        store = MemoryStore(app.state.db_path)
        try:
            proposal = ProposalTrustService(store=store).reject(proposal_id, reason=body.reason)
            return _proposal(proposal)
        finally:
            store.close()

    @app.get("/api/runtime/runs")
    def runtime_runs() -> list[dict[str, Any]]:
        with _repository(app) as repository:
            return [_dataclass(item) for item in repository.list_runs()]

    @app.get("/api/runtime/status")
    def runtime_status() -> dict[str, Any]:
        settings = load_settings(app.state.project_root)
        store = MemoryStore(app.state.db_path)
        try:
            status = build_operational_status(settings, store)
            repository = SQLiteRepository.from_memory_store(store)
            vault_path = Path(app.state.vault_path)
            markdown_files = list(vault_path.rglob("*.md")) if vault_path.exists() else []
            broken = diagnose_vault_wikilinks(vault_path) if vault_path.exists() else []
            return {
                "platform": "intelligence_hub",
                "db_path": str(app.state.db_path),
                "go_live_ready": status.go_live_ready,
                "entities": status.entity_count,
                "observations": status.observation_count,
                "decisions": status.decision_count,
                "briefs": len(repository.list_briefs()),
                "events": len(repository.list_events()),
                "insights": len(repository.list_insights()),
                "proposals": len(repository.list_proposals()),
                "proposal_metrics": _dataclass(status.proposal_metrics) if status.proposal_metrics else None,
                "latest_briefs": [_dataclass(item) for item in status.latest_briefs],
                "obsidian": {
                    "vault_path": str(vault_path),
                    "note_count": len(markdown_files),
                    "broken_link_count": len(broken),
                    "stale_count": 1 if (vault_path / "90 System" / "Stale Notes.md").exists() else 0,
                },
            }
        finally:
            store.close()

    return app


class _RepositoryContext:
    def __init__(self, db_path: Path) -> None:
        self.store = MemoryStore(db_path)
        self.repository = SQLiteRepository.from_memory_store(self.store)

    def __enter__(self) -> SQLiteRepository:
        return self.repository

    def __exit__(self, *_: object) -> None:
        self.store.close()


def _repository(app: FastAPI) -> _RepositoryContext:
    return _RepositoryContext(app.state.db_path)


def _dataclass(item: Any) -> dict[str, Any]:
    if item is None:
        return {}
    if is_dataclass(item):
        return asdict(item)
    return dict(item)


def _brief(item: Any) -> dict[str, Any]:
    data = _dataclass(item)
    data["markdown"] = f"# {item.title}\n\n{item.executive_summary}\n\n" + "\n".join(f"- {action}" for action in item.top_actions)
    return data


def _entity(item: Any) -> dict[str, Any]:
    return _dataclass(item)


def _proposal(item: Any) -> dict[str, Any]:
    data = _dataclass(item)
    data["payload"] = payload_to_dict(item.payload)
    return data


def _has_configured_db_env() -> bool:
    return bool(os.getenv("INTELLIGENCE_HUB_DB") or os.getenv("HERMES_MEMORY_DB"))


app = create_app()
