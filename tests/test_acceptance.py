from __future__ import annotations

from pathlib import Path

from core.acceptance import run_acceptance_check
from core.config import Settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path) -> Settings:
    return Settings(
        project_root=PROJECT_ROOT,
        model_provider="cloud",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen2.5:14b",
        cloud_base_url="https://api.example.com/v1",
        cloud_api_key="cloud-key",
        cloud_fast_model="fast",
        cloud_pro_model="pro",
        cloud_timeout_seconds=60.0,
        research_topic="AI agents",
        source_file=PROJECT_ROOT / "data" / "sources" / "ai_research_items.json",
        memory_db=tmp_path / "unused.sqlite",
        github_watchlist_file=PROJECT_ROOT / "data" / "watchlists" / "github_repos.json",
        paper_watchlist_file=PROJECT_ROOT / "data" / "watchlists" / "papers.json",
        domain_watchlist_file=PROJECT_ROOT / "data" / "watchlists" / "domain_signals.json",
        fixture_root=PROJECT_ROOT / "data" / "fixtures",
        github_token="github-token",
        notion_token="notion-token",
        notion_parent_page_id="parent-id",
        notion_daily_briefs_database_id="briefs-db",
        notion_papers_database_id="papers-db",
        notion_github_repos_database_id="repos-db",
        notion_ecosystem_database_id="ecosystem-db",
        notion_decisions_database_id="decisions-db",
        notion_radar_snapshots_database_id="radar-db",
        notion_radar_entities_database_id="radar-entities-db",
        telegram_bot_token="telegram-token",
        telegram_chat_id="telegram-chat",
    )


def test_acceptance_check_exercises_full_local_loop(tmp_path) -> None:
    report = run_acceptance_check(_settings(tmp_path), run_date="2026-07-02")

    assert report.ok is True
    assert report.failures == ()
    assert report.entity_count > 0
    assert report.observation_count > 0
    assert report.decision_count > 0
    assert report.brief_count >= 6
    assert report.run_count >= 6
    assert [(stage.name, stage.notion_status, stage.telegram_status) for stage in report.stages] == [
        ("daily", "published", "sent"),
        ("weekly", "published", "sent"),
        ("monthly", "published", "sent"),
        ("dashboard", "published", "sent"),
        ("radar", "published", "sent"),
        ("decision_review", "published", "sent"),
    ]
