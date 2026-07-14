from __future__ import annotations

from core.decision_review_pipeline import run_decision_review_pipeline
from core.memory import MemoryStore


class FakeNotionClient:
    def __init__(self) -> None:
        self.records = []

    def create_brief_record(self, database_id, record):
        self.records.append((database_id, record))
        return type("Page", (), {"id": "decision-review-page-id", "url": "https://notion.so/hermes-review"})()


class FakeTelegramClient:
    def __init__(self) -> None:
        self.notifications = []

    def send_notification(self, notification):
        self.notifications.append(notification)
        return type("TelegramResult", (), {"message_id": 88})()


def _seed_decision(store: MemoryStore) -> None:
    store.record_decision(
        signal_id="repo:All-Hands-AI/OpenHands",
        action="Prototype",
        rationale="Momentum crossed the weekly threshold.",
        expected_payoff="Validate agent workflow gains.",
        risk="Could duplicate existing tooling.",
        revisit_date="2026-07-07",
        confidence="high",
    )


def test_run_decision_review_pipeline_records_dry_run_brief(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        _seed_decision(store)

        result = run_decision_review_pipeline(
            store=store,
            as_of="2026-07-07",
            since="2026-07-01",
            notion_url="local://notion/decision-review-dry-run",
        )

        assert result.notion.status == "dry-run"
        assert result.telegram.status == "dry-run"
        assert result.brief.brief_type == "decision_review"
        assert result.brief.top_actions[0].startswith("Review later: Revisit Prototype decision")
        briefs = store.list_briefs(brief_type="decision_review", since="2026-07-01", until="2026-07-07")
        assert len(briefs) == 1
    finally:
        store.close()


def test_run_decision_review_pipeline_publishes_and_sends_telegram(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    notion = FakeNotionClient()
    telegram = FakeTelegramClient()
    try:
        _seed_decision(store)

        result = run_decision_review_pipeline(
            store=store,
            as_of="2026-07-07",
            since="2026-07-01",
            notion_url="local://notion/decision-review-dry-run",
            notion_client=notion,  # type: ignore[arg-type]
            notion_database_id="database-id",
            telegram_client=telegram,  # type: ignore[arg-type]
            publish_notion=True,
            send_telegram=True,
        )

        assert result.notion.status == "published"
        assert result.telegram.status == "sent"
        assert result.brief.notion_url == "https://notion.so/hermes-review"
        assert notion.records[0][0] == "database-id"
        assert notion.records[0][1].tags == ("AI Intelligence", "Decision Review")
        assert telegram.notifications[0].notion_url == "https://notion.so/hermes-review"
    finally:
        store.close()
