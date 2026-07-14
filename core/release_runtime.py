from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from connectors.obsidian import ObsidianClient
from core.config import load_settings
from core.daily_pipeline import DailyPipelineResult, run_daily_pipeline
from core.memory import MemoryStore
from core.obsidian_publisher import ObsidianPublisher, PublishResult
from core.obsidian_read_model import ObsidianReadModelBuilder
from core.obsidian_renderer import ObsidianRenderer
from core.operational_status import build_operational_status
from core.proposal_service import ProposalTrustService
from core.proposals import EntityProposalPayload, InsightProposalPayload, Proposal
from core.repository import SQLiteRepository
from core.watchlist import load_domain_watchlist, load_github_watchlist, load_paper_watchlist


DEMO_DATE = "2026-07-10"
DEMO_DIR = Path("data/demo")
DEMO_DB = DEMO_DIR / "intelligence_hub_demo.sqlite"
DEMO_VAULT = DEMO_DIR / "obsidian_vault"


@dataclass(frozen=True)
class DemoPaths:
    project_root: Path
    db_path: Path
    vault_path: Path


@dataclass(frozen=True)
class DemoSeedResult:
    db_path: Path
    vault_path: Path
    seeded: bool
    daily_result: DailyPipelineResult | None
    proposal_count: int
    insight_count: int
    event_count: int
    decision_count: int
    brief_count: int


@dataclass(frozen=True)
class ObsidianExportSummary:
    vault_path: Path
    notes_written: int
    stale_count: int
    broken_link_count: int
    result: PublishResult


def demo_paths(project_root: Path, *, db_path: Path | str | None = None, vault_path: Path | str | None = None) -> DemoPaths:
    root = project_root.resolve()
    resolved_db = Path(db_path) if db_path is not None else root / DEMO_DB
    resolved_vault = Path(vault_path) if vault_path is not None else root / DEMO_VAULT
    if not resolved_db.is_absolute():
        resolved_db = root / resolved_db
    if not resolved_vault.is_absolute():
        resolved_vault = root / resolved_vault
    return DemoPaths(project_root=root, db_path=resolved_db.resolve(), vault_path=resolved_vault.resolve())


def seed_demo(
    project_root: Path,
    *,
    db_path: Path | None = None,
    vault_path: Path | None = None,
    run_date: str = DEMO_DATE,
    force: bool = False,
) -> DemoSeedResult:
    paths = demo_paths(project_root, db_path=db_path, vault_path=vault_path)
    paths.db_path.parent.mkdir(parents=True, exist_ok=True)
    previous_platform_db = os.environ.get("INTELLIGENCE_HUB_DB")
    previous_db = os.environ.get("HERMES_MEMORY_DB")
    previous_synthesis = os.environ.get("HERMES_SYNTHESIS_MODE")
    os.environ["INTELLIGENCE_HUB_DB"] = str(paths.db_path)
    os.environ["HERMES_MEMORY_DB"] = str(paths.db_path)
    os.environ["HERMES_SYNTHESIS_MODE"] = "off"
    store = MemoryStore(paths.db_path)
    daily_result: DailyPipelineResult | None = None
    try:
        already_seeded = _has_demo_run(store, run_date)
        if force or not already_seeded:
            settings = load_settings(paths.project_root)
            daily_result = run_daily_pipeline(
                store=store,
                watchlist=load_github_watchlist(settings.github_watchlist_file),
                paper_watchlist=load_paper_watchlist(settings.paper_watchlist_file),
                domain_watchlist=load_domain_watchlist(settings.domain_watchlist_file),
                run_date=run_date,
                revisit_date="2026-07-17",
                notion_url="local://notion/demo",
                fixture_root=settings.fixture_root,
                obsidian_client=ObsidianClient(paths.vault_path),
                publish_obsidian=True,
            )
        _ensure_review_surface_proposals(store, run_date=run_date)
        export_obsidian(project_root, db_path=paths.db_path, vault_path=paths.vault_path)
        repository = SQLiteRepository.from_memory_store(store)
        return DemoSeedResult(
            db_path=paths.db_path,
            vault_path=paths.vault_path,
            seeded=force or not already_seeded,
            daily_result=daily_result,
            proposal_count=len(repository.list_proposals()),
            insight_count=len(repository.list_insights()),
            event_count=len(repository.list_events()),
            decision_count=len(repository.list_decisions()),
            brief_count=len(repository.list_briefs()),
        )
    finally:
        store.close()
        _restore_env("INTELLIGENCE_HUB_DB", previous_platform_db)
        _restore_env("HERMES_MEMORY_DB", previous_db)
        _restore_env("HERMES_SYNTHESIS_MODE", previous_synthesis)


def export_obsidian(
    project_root: Path,
    *,
    db_path: Path | None = None,
    vault_path: Path | None = None,
) -> ObsidianExportSummary:
    paths = demo_paths(project_root, db_path=db_path, vault_path=vault_path)
    store = MemoryStore(paths.db_path)
    try:
        model = ObsidianReadModelBuilder(SQLiteRepository.from_memory_store(store)).build()
        result = ObsidianPublisher(paths.vault_path).publish(model, ObsidianRenderer())
        return ObsidianExportSummary(
            vault_path=paths.vault_path,
            notes_written=len(result.written),
            stale_count=len(result.stale),
            broken_link_count=len(result.broken_wikilinks),
            result=result,
        )
    finally:
        store.close()


def reset_demo_data(project_root: Path, *, yes: bool = False) -> Path:
    demo_root = (project_root.resolve() / DEMO_DIR).resolve()
    if not yes:
        raise ValueError("reset requires explicit confirmation with --yes")
    if not _is_relative_to(demo_root, project_root.resolve() / "data"):
        raise ValueError(f"refusing to reset non-demo path: {demo_root}")
    if demo_root.exists():
        shutil.rmtree(demo_root)
    return demo_root


def platform_status(project_root: Path, *, db_path: Path | None = None) -> dict:
    paths = demo_paths(project_root, db_path=db_path)
    previous_platform_db = os.environ.get("INTELLIGENCE_HUB_DB")
    previous_db = os.environ.get("HERMES_MEMORY_DB")
    os.environ["INTELLIGENCE_HUB_DB"] = str(paths.db_path)
    os.environ["HERMES_MEMORY_DB"] = str(paths.db_path)
    settings = load_settings(paths.project_root)
    store = MemoryStore(paths.db_path)
    try:
        status = build_operational_status(settings, store)
        repository = SQLiteRepository.from_memory_store(store)
        return {
            "platform": "intelligence_hub",
            "db_path": str(paths.db_path),
            "go_live_ready": status.go_live_ready,
            "entity_count": status.entity_count,
            "observation_count": status.observation_count,
            "decision_count": status.decision_count,
            "brief_count": len(repository.list_briefs()),
            "event_count": len(repository.list_events()),
            "insight_count": len(repository.list_insights()),
            "proposal_count": len(repository.list_proposals()),
            "proposal_metrics": status.proposal_metrics,
            "latest_briefs": status.latest_briefs,
        }
    finally:
        store.close()
        _restore_env("INTELLIGENCE_HUB_DB", previous_platform_db)
        _restore_env("HERMES_MEMORY_DB", previous_db)


def _has_demo_run(store: MemoryStore, run_date: str) -> bool:
    return bool(store.list_runs(stage="daily", since=run_date, until=run_date))


def _ensure_review_surface_proposals(store: MemoryStore, *, run_date: str) -> None:
    service = ProposalTrustService(store=store)
    service.submit(
        Proposal.create(
            proposal_type="insight",
            payload=InsightProposalPayload(
                claim="Unsupported demo claim should be rejected.",
                summary="This proposal intentionally has no evidence.",
                why_it_matters="It demonstrates rejected proposal auditability.",
                evidence_refs=(),
                confidence="medium",
                generated_at=run_date,
            ),
            evidence_refs=(),
            confidence="medium",
            proposed_by="intelligence_hub.demo_seed",
            model_provider="deterministic",
            model_name="intelligence_hub.demo_seed",
            model_version="v1",
            prompt_version="demo-v1",
            created_at=f"{run_date}T00:00:00+00:00",
        )
    )
    service.submit(
        Proposal.create(
            proposal_type="entity",
            payload=EntityProposalPayload(
                kind="topic",
                canonical_name="Local-first AI operations",
                observed_at=run_date,
                tags=("demo", "operations"),
                summary="Low-confidence topic proposal retained for human review.",
            ),
            evidence_refs=("demo:review-surface",),
            confidence="low",
            proposed_by="intelligence_hub.demo_seed",
            model_provider="deterministic",
            model_name="intelligence_hub.demo_seed",
            model_version="v1",
            prompt_version="demo-v1",
            created_at=f"{run_date}T00:01:00+00:00",
        )
    )


def _restore_env(name: str, previous: str | None) -> None:
    if previous is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
