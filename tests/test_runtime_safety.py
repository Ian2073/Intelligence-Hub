from __future__ import annotations

from pathlib import Path

from core.config import Settings
from core.runtime_safety import validate_memory_target_for_run


def _settings(root: Path, memory_db: Path) -> Settings:
    return Settings(
        project_root=root,
        model_provider="cloud",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen2.5:14b",
        cloud_base_url="https://api.openai.com/v1",
        cloud_api_key=None,
        cloud_fast_model="fast",
        cloud_pro_model="pro",
        cloud_timeout_seconds=60,
        research_topic="AI",
        source_file=root / "data" / "sources.json",
        memory_db=memory_db,
        github_watchlist_file=root / "data" / "github.json",
        paper_watchlist_file=root / "data" / "papers.json",
        domain_watchlist_file=root / "data" / "domains.json",
        fixture_root=root / "data" / "fixtures",
        github_token=None,
        notion_token=None,
        notion_parent_page_id=None,
        notion_daily_briefs_database_id=None,
        notion_papers_database_id=None,
        notion_github_repos_database_id=None,
        notion_ecosystem_database_id=None,
        notion_decisions_database_id=None,
        notion_radar_snapshots_database_id=None,
        notion_radar_entities_database_id=None,
        telegram_bot_token=None,
        telegram_chat_id=None,
    )


def test_validate_memory_target_blocks_local_dry_run_against_default_memory(tmp_path) -> None:
    settings = _settings(tmp_path, tmp_path / "data" / "hermes_memory.sqlite")

    message = validate_memory_target_for_run(
        settings,
        publish_notion=False,
        notion_url="local://notion/dry-run",
        operation="Daily intelligence",
    )

    assert message is not None
    assert "dry-run output would write to production memory" in message


def test_validate_memory_target_allows_isolated_or_published_runs(tmp_path) -> None:
    isolated = _settings(tmp_path, tmp_path / "tests" / ".capability" / "memory.sqlite")
    production = _settings(tmp_path, tmp_path / "data" / "hermes_memory.sqlite")

    assert validate_memory_target_for_run(
        isolated,
        publish_notion=False,
        notion_url="local://notion/dry-run",
        operation="Daily intelligence",
    ) is None
    assert validate_memory_target_for_run(
        production,
        publish_notion=True,
        notion_url="local://notion/dry-run",
        operation="Daily intelligence",
    ) is None
