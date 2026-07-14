from __future__ import annotations

from core.memory import MemoryStore
from core.notification_outbox import flush_pending_notifications


class FakeTelegramClient:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.notifications = []

    def send_notification(self, notification):
        self.notifications.append(notification)
        if self.fail:
            raise RuntimeError("telegram unavailable")
        return type("TelegramResult", (), {"message_id": 123})()


def test_flush_pending_notifications_marks_sent(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    telegram = FakeTelegramClient()
    try:
        store.enqueue_notification(
            title="Hermes Daily",
            decisions=("Read: paper",),
            top_action="Read",
            notion_url="https://notion.so/daily",
            last_error="skipped: Missing Telegram client.",
        )

        sent = flush_pending_notifications(store=store, telegram_client=telegram)  # type: ignore[arg-type]

        assert len(sent) == 1
        assert sent[0].status == "sent"
        assert telegram.notifications[0].notion_url == "https://notion.so/daily"
        assert store.list_notification_outbox(status="pending") == []
    finally:
        store.close()


def test_flush_pending_notifications_keeps_failed_items_pending(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    telegram = FakeTelegramClient(fail=True)
    try:
        record = store.enqueue_notification(
            title="Hermes Daily",
            decisions=("Read: paper",),
            top_action="Read",
            notion_url="https://notion.so/daily",
            last_error="skipped: Missing Telegram client.",
        )

        sent = flush_pending_notifications(store=store, telegram_client=telegram)  # type: ignore[arg-type]

        pending = store.list_notification_outbox(status="pending")
        assert sent == ()
        assert pending[0].id == record.id
        assert pending[0].attempts == 1
        assert "telegram unavailable" in pending[0].last_error
    finally:
        store.close()
