from __future__ import annotations

from core.memory import MemoryStore
from core.period_pipeline import run_monthly_pipeline


class FakeNotionClient:
    def __init__(self) -> None:
        self.records = []

    def create_brief_record(self, database_id, record):
        self.records.append((database_id, record))
        return type("Page", (), {"id": "monthly-page-id", "url": "https://notion.so/hermes-monthly"})()


class FakeTelegramClient:
    def __init__(self) -> None:
        self.notifications = []

    def send_notification(self, notification):
        self.notifications.append(notification)
        return type("TelegramResult", (), {"message_id": 88})()


class FakeModelRouter:
    def __init__(self) -> None:
        self.calls = []

    def generate(self, prompt, *, tier="fast"):
        self.calls.append((prompt, tier))
        return "Model-written monthly executive summary."


def _seed_memory(store: MemoryStore) -> None:
    store.record_brief(
        brief_type="weekly",
        domain="AI Intelligence",
        period_start="2026-07-01",
        period_end="2026-07-07",
        title="Intelligence Hub Weekly Brief - 2026-07-01 to 2026-07-07",
        executive_summary="Weekly movement.",
        top_actions=("Prototype: Paper connects to implementation.",),
        notion_status="dry-run",
        notion_url="local://notion/weekly",
        telegram_status="dry-run",
        telegram_detail="Telegram send not requested.",
    )


def test_run_monthly_pipeline_records_dry_run_brief(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        _seed_memory(store)

        result = run_monthly_pipeline(
            store=store,
            period_start="2026-07-01",
            period_end="2026-07-31",
            notion_url="local://notion/monthly-dry-run",
        )

        assert result.notion.status == "dry-run"
        assert result.telegram.status == "dry-run"
        assert result.brief.brief_type == "monthly"
        monthly = store.list_briefs(brief_type="monthly", since="2026-07-01", until="2026-07-31")
        assert len(monthly) == 1
    finally:
        store.close()


def test_run_monthly_pipeline_publishes_and_sends_telegram_with_notion_link(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    notion = FakeNotionClient()
    telegram = FakeTelegramClient()
    model_router = FakeModelRouter()
    try:
        _seed_memory(store)

        result = run_monthly_pipeline(
            store=store,
            period_start="2026-07-01",
            period_end="2026-07-31",
            notion_url="local://notion/monthly-dry-run",
            notion_client=notion,  # type: ignore[arg-type]
            notion_database_id="database-id",
            telegram_client=telegram,  # type: ignore[arg-type]
            model_router=model_router,  # type: ignore[arg-type]
            publish_notion=True,
            send_telegram=True,
        )

        assert result.notion.status == "published"
        assert result.brief.executive_summary == "Model-written monthly executive summary."
        assert model_router.calls[0][1] == "pro"
        assert result.telegram.status == "sent"
        assert result.brief.notion_url == "https://notion.so/hermes-monthly"
        assert notion.records[0][1].tags == ("AI Intelligence", "Monthly Report")
        assert telegram.notifications[0].notion_url == "https://notion.so/hermes-monthly"
    finally:
        store.close()
