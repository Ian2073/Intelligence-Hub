from __future__ import annotations

from core.memory import MemoryStore
from core.weekly_pipeline import run_weekly_pipeline


class FakeNotionClient:
    def __init__(self) -> None:
        self.records = []

    def create_brief_record(self, database_id, record):
        self.records.append((database_id, record))
        return type("Page", (), {"id": "weekly-page-id", "url": "https://notion.so/hermes-weekly"})()


class FakeTelegramClient:
    def __init__(self) -> None:
        self.notifications = []

    def send_notification(self, notification):
        self.notifications.append(notification)
        return type("TelegramResult", (), {"message_id": 77})()


class FailingNotionClient:
    def create_brief_record(self, database_id, record):
        raise RuntimeError("notion unavailable")


class FailingTelegramClient:
    def send_notification(self, notification):
        raise RuntimeError("telegram unavailable")


class FakeModelRouter:
    def __init__(self) -> None:
        self.calls = []

    def generate(self, prompt, *, tier="fast"):
        self.calls.append((prompt, tier))
        return "Model-written weekly executive summary."


def _seed_memory(store: MemoryStore) -> None:
    entity = store.upsert_entity(
        kind="repository",
        canonical_name="All-Hands-AI/OpenHands",
        observed_at="2026-07-02",
    )
    store.record_observation(
        entity_id=entity.id,
        observed_at="2026-07-02",
        source_type="github",
        source_url="https://github.com/All-Hands-AI/OpenHands",
        metric_name="stars",
        previous_value=24000,
        current_value=25500,
        raw_evidence="GitHub snapshot.",
        confidence="high",
    )
    store.record_brief(
        brief_type="daily",
        domain="AI Intelligence",
        period_start="2026-07-02",
        period_end="2026-07-02",
        title="Intelligence Hub Daily Brief - 2026-07-02",
        executive_summary="Open-source AI engineering moved.",
        top_actions=("Prototype: OpenHands has strong momentum.",),
        notion_status="dry-run",
        notion_url="local://notion/dry-run",
        telegram_status="dry-run",
        telegram_detail="Telegram send not requested.",
    )
    store.record_decision(
        signal_id="repo:All-Hands-AI/OpenHands",
        action="Prototype",
        rationale="Momentum crossed the weekly threshold.",
        expected_payoff="Validate agent workflow gains.",
        risk="Could duplicate existing tooling.",
        revisit_date="2026-07-07",
        confidence="high",
    )


def test_run_weekly_pipeline_records_dry_run_brief(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        _seed_memory(store)

        result = run_weekly_pipeline(
            store=store,
            period_start="2026-07-01",
            period_end="2026-07-07",
            notion_url="local://notion/weekly-dry-run",
        )

        assert result.notion.status == "dry-run"
        assert result.telegram.status == "dry-run"
        assert result.brief.brief_type == "weekly"
        assert result.brief.top_actions[0] == "Prototype: OpenHands has strong momentum."
        assert result.brief.top_actions[1].startswith("Review later: Revisit Prototype decision")
        weekly = store.list_briefs(brief_type="weekly", since="2026-07-01", until="2026-07-07")
        assert len(weekly) == 1
    finally:
        store.close()


def test_run_weekly_pipeline_publishes_and_sends_telegram_with_notion_link(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    notion = FakeNotionClient()
    telegram = FakeTelegramClient()
    model_router = FakeModelRouter()
    try:
        _seed_memory(store)

        result = run_weekly_pipeline(
            store=store,
            period_start="2026-07-01",
            period_end="2026-07-07",
            notion_url="local://notion/weekly-dry-run",
            notion_client=notion,  # type: ignore[arg-type]
            notion_database_id="database-id",
            telegram_client=telegram,  # type: ignore[arg-type]
            model_router=model_router,  # type: ignore[arg-type]
            publish_notion=True,
            send_telegram=True,
        )

        assert result.notion.status == "published"
        assert result.brief.executive_summary == "Model-written weekly executive summary."
        assert model_router.calls[0][1] == "pro"
        assert result.telegram.status == "sent"
        assert result.brief.notion_url == "https://notion.so/hermes-weekly"
        assert notion.records[0][0] == "database-id"
        assert notion.records[0][1].tags == ("AI Intelligence", "Weekly Report")
        assert "Decision reviews:" in notion.records[0][1].body
        assert telegram.notifications[0].notion_url == "https://notion.so/hermes-weekly"
    finally:
        store.close()


def test_run_weekly_pipeline_records_notion_failure_and_skips_telegram(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    telegram = FakeTelegramClient()
    try:
        _seed_memory(store)

        result = run_weekly_pipeline(
            store=store,
            period_start="2026-07-01",
            period_end="2026-07-07",
            notion_url="local://notion/weekly-dry-run",
            notion_client=FailingNotionClient(),  # type: ignore[arg-type]
            notion_database_id="database-id",
            telegram_client=telegram,  # type: ignore[arg-type]
            publish_notion=True,
            send_telegram=True,
        )

        assert result.notion.status == "failed"
        assert "notion unavailable" in result.notion.detail
        assert result.telegram.status == "skipped"
        assert result.brief.notion_status == "failed"
        assert result.brief.telegram_status == "skipped"
        assert telegram.notifications == []
    finally:
        store.close()


def test_run_weekly_pipeline_records_telegram_failure(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    notion = FakeNotionClient()
    try:
        _seed_memory(store)

        result = run_weekly_pipeline(
            store=store,
            period_start="2026-07-01",
            period_end="2026-07-07",
            notion_url="local://notion/weekly-dry-run",
            notion_client=notion,  # type: ignore[arg-type]
            notion_database_id="database-id",
            telegram_client=FailingTelegramClient(),  # type: ignore[arg-type]
            publish_notion=True,
            send_telegram=True,
        )

        assert result.notion.status == "published"
        assert result.telegram.status == "failed"
        assert "telegram unavailable" in result.telegram.detail
        assert result.brief.telegram_status == "failed"
    finally:
        store.close()
