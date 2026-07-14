from __future__ import annotations

from connectors.telegram import TelegramClient, TelegramNotification
from core.delivery import DeliveryStatus
from core.memory import MemoryStore, NotificationOutboxRecord


def enqueue_unsent_telegram_notification(
    *,
    store: MemoryStore,
    notification: TelegramNotification,
    notion_status: DeliveryStatus,
    telegram_status: DeliveryStatus,
    send_telegram: bool,
) -> NotificationOutboxRecord | None:
    if not send_telegram:
        return None
    if notion_status.status != "published":
        return None
    if telegram_status.status == "sent":
        return None
    return store.enqueue_notification(
        title=notification.title,
        decisions=notification.decisions,
        top_action=notification.top_action,
        notion_url=notification.notion_url,
        last_error=f"{telegram_status.status}: {telegram_status.detail}",
    )


def flush_pending_notifications(
    *,
    store: MemoryStore,
    telegram_client: TelegramClient,
    limit: int | None = None,
) -> tuple[NotificationOutboxRecord, ...]:
    pending = store.list_notification_outbox(status="pending")
    if limit is not None:
        pending = pending[:limit]
    flushed: list[NotificationOutboxRecord] = []
    for record in pending:
        notification = TelegramNotification(
            title=record.title,
            decisions=record.decisions,
            top_action=record.top_action,
            notion_url=record.notion_url,
        )
        try:
            telegram_client.send_notification(notification)
        except Exception as exc:
            store.mark_notification_failed(record.id, error=f"{exc.__class__.__name__}: {str(exc)[:450]}")
            continue
        flushed.append(store.mark_notification_sent(record.id))
    return tuple(flushed)
