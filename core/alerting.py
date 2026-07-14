from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from connectors.telegram import TelegramClient, TelegramNotification
from core.config import Settings
from core.delivery import DeliveryStatus, failed_delivery
from core.memory import MemoryStore, RunRecord


@dataclass(frozen=True)
class PipelineAlertResult:
    run: RunRecord
    telegram: DeliveryStatus


def send_pipeline_alert(
    *,
    store: MemoryStore,
    pipeline: str,
    error: Exception,
    settings: Settings,
    telegram_client: TelegramClient | None = None,
    occurred_at: datetime | None = None,
    rate_limit_minutes: int = 60,
) -> PipelineAlertResult:
    occurred = occurred_at or datetime.now(timezone.utc).replace(microsecond=0)
    error_summary = _summarize_error(error)
    if _has_recent_sent_alert(store, pipeline=pipeline, occurred_at=occurred, minutes=rate_limit_minutes):
        status = DeliveryStatus(
            channel="telegram",
            status="skipped",
            detail=f"Pipeline alert rate-limited for {pipeline}.",
        )
    elif telegram_client is None and settings.telegram_enabled:
        telegram_client = TelegramClient(settings.telegram_bot_token or "", settings.telegram_chat_id or "")
        status = _send_alert(telegram_client, pipeline=pipeline, error_summary=error_summary, occurred_at=occurred)
    elif telegram_client is not None:
        status = _send_alert(telegram_client, pipeline=pipeline, error_summary=error_summary, occurred_at=occurred)
    else:
        status = DeliveryStatus(
            channel="telegram",
            status="skipped",
            detail="Telegram alert skipped: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not both set.",
        )

    run = store.record_run(
        run_date=occurred.date().isoformat(),
        stage=pipeline,
        title=f"Hermes Alert: {pipeline} failed",
        period_start=occurred.date().isoformat(),
        period_end=occurred.date().isoformat(),
        status="failed",
        notion_status="skipped",
        notion_url="",
        telegram_status=status.status,
        telegram_detail=status.detail,
        created_at=occurred.isoformat(),
    )
    return PipelineAlertResult(run=run, telegram=status)


def _send_alert(
    telegram_client: TelegramClient,
    *,
    pipeline: str,
    error_summary: str,
    occurred_at: datetime,
) -> DeliveryStatus:
    notification = TelegramNotification(
        title=f"Hermes Alert: {pipeline} failed at {occurred_at.isoformat()}",
        decisions=(error_summary,),
        top_action="Investigate",
        notion_url="local://hermes/pipeline-alert",
    )
    try:
        result = telegram_client.send_notification(notification)
        return DeliveryStatus(channel="telegram", status="sent", detail=str(result.message_id))
    except Exception as exc:
        return failed_delivery("telegram", exc)


def _has_recent_sent_alert(
    store: MemoryStore,
    *,
    pipeline: str,
    occurred_at: datetime,
    minutes: int,
) -> bool:
    cutoff = occurred_at - timedelta(minutes=minutes)
    for run in reversed(store.list_runs(stage=pipeline)):
        if run.status != "failed" or run.telegram_status != "sent":
            continue
        created = _parse_datetime(run.created_at)
        if created is not None and cutoff <= created <= occurred_at:
            return True
    return False


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _summarize_error(error: Exception, limit: int = 500) -> str:
    text = f"{type(error).__name__}: {error}"
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "..."
