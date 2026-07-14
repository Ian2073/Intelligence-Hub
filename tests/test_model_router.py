from __future__ import annotations

from core.config import Settings
from core.model_policy import tier_for_task
from core.model_router import ModelRouter


def _settings(tmp_path, **overrides) -> Settings:
    defaults = {
        "project_root": tmp_path,
        "model_provider": "cloud",
        "ollama_base_url": "http://localhost:11434",
        "ollama_model": "qwen2.5:14b",
        "cloud_base_url": "https://api.example.com/v1",
        "cloud_api_key": "cloud-key",
        "cloud_fast_model": "cheap-fast",
        "cloud_pro_model": "strong-pro",
        "cloud_timeout_seconds": 60.0,
        "research_topic": "AI agents",
        "source_file": tmp_path / "data" / "sources" / "ai_research_items.json",
        "memory_db": tmp_path / "data" / "hermes_memory.sqlite",
        "github_watchlist_file": tmp_path / "data" / "watchlists" / "github_repos.json",
        "paper_watchlist_file": tmp_path / "data" / "watchlists" / "papers.json",
        "domain_watchlist_file": tmp_path / "data" / "watchlists" / "domain_signals.json",
        "fixture_root": tmp_path / "data" / "fixtures",
        "github_token": None,
        "notion_token": None,
        "notion_parent_page_id": None,
        "notion_daily_briefs_database_id": None,
        "notion_papers_database_id": None,
        "notion_github_repos_database_id": None,
        "notion_ecosystem_database_id": None,
        "notion_decisions_database_id": None,
        "notion_radar_snapshots_database_id": None,
        "notion_radar_entities_database_id": None,
        "telegram_bot_token": None,
        "telegram_chat_id": None,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_model_router_selects_cloud_fast_and_pro_models(tmp_path, monkeypatch) -> None:
    created = []

    class FakeCloudClient:
        def __init__(self, base_url, api_key, model, timeout):
            created.append((base_url, api_key, model, timeout))

        def generate(self, prompt):
            return f"answer:{prompt}"

    monkeypatch.setattr("core.model_router.OpenAICompatibleClient", FakeCloudClient)
    router = ModelRouter(_settings(tmp_path))

    assert router.generate("classify", tier="fast") == "answer:classify"
    assert router.generate("decide", tier="pro") == "answer:decide"
    assert created[0][2] == "cheap-fast"
    assert created[1][2] == "strong-pro"


def test_model_policy_routes_decision_work_to_pro_and_simple_work_to_fast() -> None:
    assert tier_for_task("research_brief") == "pro"
    assert tier_for_task("weekly synthesis") == "pro"
    assert tier_for_task("classification") == "fast"
    assert tier_for_task("unknown task") == "fast"
