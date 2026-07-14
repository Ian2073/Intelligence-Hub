from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from core.api import create_app
from core.obsidian_publisher import diagnose_vault_wikilinks
from core.release_runtime import export_obsidian, reset_demo_data, seed_demo
from scripts.intelligence_hub import main as platform_cli


def test_zero_secret_demo_seed_is_idempotent_and_exports_obsidian(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.sqlite"
    vault_path = tmp_path / "vault"

    first = seed_demo(Path.cwd(), db_path=db_path, vault_path=vault_path)
    second = seed_demo(Path.cwd(), db_path=db_path, vault_path=vault_path)

    assert first.proposal_count == second.proposal_count
    assert first.insight_count == second.insight_count
    assert first.event_count == second.event_count
    assert first.decision_count == second.decision_count
    assert first.brief_count == second.brief_count
    assert first.insight_count >= 1
    assert first.event_count >= 1
    assert first.decision_count >= 1
    assert (vault_path / "02 Insights").is_dir()
    assert (vault_path / "90 System" / "Rejected Proposals.md").is_file()
    assert (vault_path / "90 System" / "Needs Review.md").is_file()
    assert diagnose_vault_wikilinks(vault_path) == []


def test_platform_api_dashboard_and_proposal_review(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.sqlite"
    vault_path = tmp_path / "vault"
    seed_demo(Path.cwd(), db_path=db_path, vault_path=vault_path)
    app = create_app(project_root=Path.cwd(), db_path=db_path, vault_path=vault_path)
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "ok", "platform": "intelligence_hub"}
    assert client.get("/ready").json()["ready"] is True
    assert "Information → Evidence" in client.get("/").text
    assert client.get("/openapi.json").status_code == 200

    briefs = client.get("/api/briefs").json()
    insights = client.get("/api/insights").json()
    entities = client.get("/api/entities").json()
    events = client.get("/api/events").json()
    decisions = client.get("/api/decisions").json()
    proposals = client.get("/api/proposals").json()
    status = client.get("/api/runtime/status").json()

    assert briefs and insights and entities and events and decisions and proposals
    assert status["obsidian"]["broken_link_count"] == 0
    assert status["proposal_metrics"]["proposals_accepted"] >= 1

    brief_id = briefs[0]["id"]
    insight_id = insights[0]["id"]
    entity_id = entities[0]["id"]
    proposal_id = next(item["id"] for item in proposals if item["validation_status"] == "needs_review")
    rejected_id = next(item["id"] for item in proposals if item["validation_status"] == "rejected")

    assert client.get(f"/api/briefs/{brief_id}").json()["id"] == brief_id
    assert client.get(f"/api/insights/{insight_id}").json()["id"] == insight_id
    assert client.get(f"/api/entities/{entity_id}").json()["id"] == entity_id
    assert client.get(f"/api/proposals/{proposal_id}").json()["id"] == proposal_id
    assert client.get("/api/briefs/missing").json()["error"] == "not_found"
    assert client.post(f"/api/proposals/{rejected_id}/revalidate").json()["validation_status"] == "rejected"
    assert client.post(f"/api/proposals/{proposal_id}/accept").json()["validation_status"] == "accepted"
    assert (
        client.post(
            f"/api/proposals/{proposal_id}/reject",
            json={"reason": "release candidate smoke"},
        ).json()["validation_status"]
        == "rejected"
    )


def test_platform_cli_seed_export_status_and_safe_reset(tmp_path: Path, monkeypatch, capsys) -> None:
    db_path = tmp_path / "demo.sqlite"
    vault_path = tmp_path / "vault"
    monkeypatch.setenv("HERMES_MEMORY_DB", str(db_path))

    assert platform_cli(["--db", str(db_path), "--vault", str(vault_path), "seed-demo"]) == 0
    assert "proposals=" in capsys.readouterr().out
    assert platform_cli(["--db", str(db_path), "--vault", str(vault_path), "export-obsidian"]) == 0
    assert "broken_links=0" in capsys.readouterr().out
    assert platform_cli(["--db", str(db_path), "status"]) == 0
    assert "Intelligence Hub Status" in capsys.readouterr().out

    try:
        reset_demo_data(Path.cwd(), yes=False)
    except ValueError as exc:
        assert "--yes" in str(exc)
    else:
        raise AssertionError("reset_demo_data should require explicit confirmation")
