from __future__ import annotations

from core.dashboard_pipeline import run_dashboard_pipeline
from core.memory import MemoryStore


class FakeNotionClient:
    def __init__(self) -> None:
        self.pages = []

    def create_page(self, title, body):
        self.pages.append((title, body))
        return type("Page", (), {"id": "dashboard-page-id", "url": "https://notion.so/hermes-dashboard"})()


class FakeTelegramClient:
    def __init__(self) -> None:
        self.notifications = []

    def send_notification(self, notification):
        self.notifications.append(notification)
        return type("TelegramResult", (), {"message_id": 99})()


class FakeModelRouter:
    def __init__(self) -> None:
        self.calls = []

    def generate(self, prompt, *, tier="fast"):
        self.calls.append((prompt, tier))
        return "Model-written dashboard executive summary."


def _seed_memory(store: MemoryStore) -> None:
    store.record_brief(
        brief_type="daily",
        domain="AI Intelligence",
        period_start="2026-07-08",
        period_end="2026-07-08",
        title="Intelligence Hub Daily Brief - 2026-07-08",
        executive_summary="Daily summary.",
        top_actions=("Prototype: Paper connects to implementation.",),
        notion_status="dry-run",
        notion_url="local://notion/daily",
        telegram_status="dry-run",
        telegram_detail="Telegram send not requested.",
    )


def test_run_dashboard_pipeline_dry_run(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        _seed_memory(store)

        result = run_dashboard_pipeline(
            store=store,
            as_of="2026-07-08",
            window_start="2026-07-01",
            notion_url="local://notion/dashboard",
        )

        assert result.notion.status == "dry-run"
        assert result.telegram.status == "dry-run"
        assert result.dashboard.top_actions == ("Prototype: Paper connects to implementation.",)
        assert result.brief.brief_type == "dashboard"
        assert result.brief.notion_status == "dry-run"
        assert store.list_briefs(brief_type="dashboard")
    finally:
        store.close()


def test_run_dashboard_pipeline_publishes_and_sends_telegram(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    notion = FakeNotionClient()
    telegram = FakeTelegramClient()
    model_router = FakeModelRouter()
    try:
        _seed_memory(store)

        result = run_dashboard_pipeline(
            store=store,
            as_of="2026-07-08",
            window_start="2026-07-01",
            notion_url="local://notion/dashboard",
            notion_client=notion,  # type: ignore[arg-type]
            telegram_client=telegram,  # type: ignore[arg-type]
            model_router=model_router,  # type: ignore[arg-type]
            publish_notion=True,
            send_telegram=True,
        )

        assert result.notion.status == "published"
        assert result.dashboard.executive_summary == "Model-written dashboard executive summary."
        assert model_router.calls[0][1] == "pro"
        assert result.telegram.status == "sent"
        assert result.brief.notion_url == "https://notion.so/hermes-dashboard"
        assert result.brief.telegram_status == "sent"
        assert notion.pages[0][0] == "Intelligence Hub Executive Dashboard - 2026-07-08"
        assert "Latest intelligence:" in notion.pages[0][1]
        assert "Operational health:" in notion.pages[0][1]
        assert "Memory tables:" in notion.pages[0][1]
        assert telegram.notifications[0].notion_url == "https://notion.so/hermes-dashboard"
    finally:
        store.close()
