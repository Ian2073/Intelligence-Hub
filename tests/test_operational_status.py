from __future__ import annotations

from core.config import Settings
from core.memory import MemoryStore
from core.operational_status import build_operational_status, get_health_metrics, render_operational_status


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
        "notion_token": "notion-token",
        "notion_parent_page_id": "parent-id",
        "notion_daily_briefs_database_id": "daily-db",
        "notion_papers_database_id": "papers-db",
        "notion_github_repos_database_id": "repos-db",
        "notion_ecosystem_database_id": "ecosystem-db",
        "notion_decisions_database_id": "decisions-db",
        "notion_radar_snapshots_database_id": "radar-db",
        "notion_radar_entities_database_id": "entities-db",
        "telegram_bot_token": None,
        "telegram_chat_id": None,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_operational_status_reports_latest_briefs_and_go_live_gaps(tmp_path) -> None:
    store = MemoryStore(tmp_path / "data" / "memory.sqlite")
    try:
        store.upsert_entity(
            kind="repository",
            canonical_name="OpenHands",
            observed_at="2026-07-02",
            tags=("github",),
        )
        store.record_observation(
            entity_id=store.list_entities()[0].id,
            observed_at="2026-07-02",
            source_type="github",
            source_url="https://github.com/All-Hands-AI/OpenHands",
            metric_name="stars",
            previous_value=24000,
            current_value=25500,
            raw_evidence="GitHub repo snapshot",
            confidence="high",
        )
        store.record_decision(
            signal_id="github-repo:OpenHands:2026-07-02",
            action="Prototype",
            rationale="Momentum increased.",
            expected_payoff="Validate engineering value.",
            risk="May be noisy.",
            revisit_date="2026-07-09",
            confidence="medium",
        )
        store.record_brief(
            brief_type="daily",
            domain="AI Intelligence",
            period_start="2026-07-01",
            period_end="2026-07-01",
            title="Older Daily",
            executive_summary="Older summary",
            top_actions=("Watch: older",),
            notion_status="dry-run",
            notion_url="local://notion/older",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
        )
        store.record_brief(
            brief_type="daily",
            domain="AI Intelligence",
            period_start="2026-07-03",
            period_end="2026-07-03",
            title="Later Dry Run",
            executive_summary="Later dry-run summary",
            top_actions=("Watch: later",),
            notion_status="dry-run",
            notion_url="local://notion/later",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
        )
        store.record_brief(
            brief_type="daily",
            domain="AI Intelligence",
            period_start="2026-07-02",
            period_end="2026-07-02",
            title="Hermes Daily Intelligence - 2026-07-02",
            executive_summary="Latest summary",
            top_actions=("Prototype: OpenHands",),
            notion_status="published",
            notion_url="https://notion.so/hermes-daily",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
        )
        store.record_brief(
            brief_type="daily",
            domain="AI Intelligence",
            period_start="2026-07-23",
            period_end="2026-07-23",
            title="Future Dry Run",
            executive_summary="Future dry-run summary",
            top_actions=("Watch: future",),
            notion_status="dry-run",
            notion_url="local://notion/future",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
        )

        status = build_operational_status(_settings(tmp_path), store, as_of="2026-07-03")
        rendered = render_operational_status(status)

        assert status.go_live_ready is False
        assert [gap.name for gap in status.credential_gaps] == [
            "GITHUB_TOKEN",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHAT_ID",
        ]
        assert status.entity_count == 1
        assert status.observation_count == 1
        assert status.decision_count == 1
        assert status.pending_notification_count == 0
        assert status.latest_briefs[0].title == "Hermes Daily Intelligence - 2026-07-02"
        assert "Notion=published Telegram=dry-run URL=https://notion.so/hermes-daily source=brief" in rendered
        assert "scripts\\github_check.py" in rendered
        assert "scripts\\telegram_check.py" in rendered

        future_status = build_operational_status(_settings(tmp_path), store, as_of="2026-07-02", include_future=True)
        assert future_status.latest_briefs[0].title == "Hermes Daily Intelligence - 2026-07-02"
        metrics = get_health_metrics(store, since="2026-07-01", until="2026-07-03")
        assert metrics.table_counts["entities"] == 1
        assert metrics.table_counts["briefs"] == 4
    finally:
        store.close()


def test_operational_status_prefers_latest_run_ledger_over_brief_fallback(tmp_path) -> None:
    store = MemoryStore(tmp_path / "data" / "memory.sqlite")
    try:
        store.record_brief(
            brief_type="weekly",
            domain="AI Intelligence",
            period_start="2026-07-01",
            period_end="2026-07-07",
            title="Older Published Weekly",
            executive_summary="Older summary",
            top_actions=("Watch: older",),
            notion_status="published",
            notion_url="https://notion.so/older-weekly",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
        )
        store.record_run(
            run_date="2026-07-03",
            stage="weekly",
            title="Hermes Weekly Intelligence - 2026-06-29 to 2026-07-05",
            period_start="2026-06-29",
            period_end="2026-07-05",
            status="completed",
            notion_status="published",
            notion_url="https://notion.so/latest-run-weekly",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
            created_at="2026-07-03T01:00:00+00:00",
        )

        status = build_operational_status(_settings(tmp_path), store, as_of="2026-07-03")
        rendered = render_operational_status(status)

        assert status.latest_briefs[0].title == "Hermes Weekly Intelligence - 2026-06-29 to 2026-07-05"
        assert "URL=https://notion.so/latest-run-weekly source=run" in rendered
    finally:
        store.close()


def test_operational_status_does_not_let_dry_run_ledger_hide_published_brief(tmp_path) -> None:
    store = MemoryStore(tmp_path / "data" / "memory.sqlite")
    try:
        store.record_brief(
            brief_type="daily",
            domain="AI Intelligence",
            period_start="2026-07-03",
            period_end="2026-07-03",
            title="Published Daily",
            executive_summary="Published summary",
            top_actions=("Read: published",),
            notion_status="published",
            notion_url="https://notion.so/published-daily",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
        )
        store.record_run(
            run_date="2026-07-03",
            stage="daily",
            title="Dry Run Daily",
            period_start="2026-07-03",
            period_end="2026-07-03",
            status="completed",
            notion_status="dry-run",
            notion_url="local://notion/dry-run",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
            created_at="2026-07-03T02:00:00+00:00",
        )

        status = build_operational_status(_settings(tmp_path), store, as_of="2026-07-03")

        assert status.latest_briefs[0].title == "Published Daily"
        assert status.latest_briefs[0].source == "brief"
    finally:
        store.close()


def test_operational_status_is_ready_when_required_credentials_exist(tmp_path) -> None:
    store = MemoryStore(tmp_path / "data" / "memory.sqlite")
    try:
        status = build_operational_status(
            _settings(
                tmp_path,
                github_token="github-token",
                telegram_bot_token="telegram-token",
                telegram_chat_id="telegram-chat",
            ),
            store,
        )

        assert status.go_live_ready is True
        assert status.credential_gaps == ()
    finally:
        store.close()
