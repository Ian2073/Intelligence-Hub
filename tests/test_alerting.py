from __future__ import annotations

from datetime import datetime, timezone

from core.alerting import send_pipeline_alert
from core.config import Settings
from core.memory import MemoryStore


class FakeTelegramClient:
    def __init__(self) -> None:
        self.notifications = []

    def send_notification(self, notification):
        self.notifications.append(notification)
        return type("TelegramResult", (), {"message_id": 77})()


def _settings(tmp_path, **overrides) -> Settings:
    defaults = {
        "project_root": tmp_path,
        "model_provider": "cloud",
        "ollama_base_url": "http://localhost:11434",
        "ollama_model": "qwen2.5:14b",
        "cloud_base_url": "https://api.example.com/v1",
        "cloud_api_key": "cloud-key",
        "cloud_fast_model": "fast",
        "cloud_pro_model": "pro",
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
        "telegram_bot_token": "telegram-token",
        "telegram_chat_id": "telegram-chat",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_send_pipeline_alert_sends_telegram_and_records_failed_run(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    telegram = FakeTelegramClient()
    try:
        result = send_pipeline_alert(
            store=store,
            pipeline="daily",
            error=RuntimeError("fixture blew up"),
            settings=_settings(tmp_path),
            telegram_client=telegram,  # type: ignore[arg-type]
            occurred_at=datetime(2026, 7, 9, 3, 0, tzinfo=timezone.utc),
        )

        assert result.telegram.status == "sent"
        assert result.run.status == "failed"
        assert result.run.telegram_status == "sent"
        assert telegram.notifications[0].title.startswith("Intelligence Hub Alert: daily failed at")
        assert telegram.notifications[0].decisions == ("RuntimeError: fixture blew up",)
        assert store.list_runs(stage="daily")[0].title == "Intelligence Hub Alert: daily failed"
    finally:
        store.close()


def test_send_pipeline_alert_rate_limits_repeated_failure_per_pipeline(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    telegram = FakeTelegramClient()
    try:
        first = send_pipeline_alert(
            store=store,
            pipeline="dashboard",
            error=RuntimeError("first failure"),
            settings=_settings(tmp_path),
            telegram_client=telegram,  # type: ignore[arg-type]
            occurred_at=datetime(2026, 7, 9, 3, 0, tzinfo=timezone.utc),
        )
        second = send_pipeline_alert(
            store=store,
            pipeline="dashboard",
            error=RuntimeError("second failure"),
            settings=_settings(tmp_path),
            telegram_client=telegram,  # type: ignore[arg-type]
            occurred_at=datetime(2026, 7, 9, 3, 30, tzinfo=timezone.utc),
        )

        assert first.telegram.status == "sent"
        assert second.telegram.status == "skipped"
        assert "rate-limited" in second.telegram.detail
        assert len(telegram.notifications) == 1
        assert len(store.list_runs(stage="dashboard")) == 2
    finally:
        store.close()
