from __future__ import annotations

from dataclasses import dataclass

from connectors.notion import NotionClient, PublishedPage
from connectors.telegram import TelegramClient, TelegramNotification, TelegramResult
from core.delivery import DeliveryStatus, failed_delivery, telegram_blocked_by_notion
from core.intelligence_brief import IntelligenceBrief, SynthesisMetadata, top_actions_to_intelligence_brief
from core.intelligence_synthesis import TieredGenerator, synthesize_dashboard_summary
from core.memory import BriefRecord, MemoryStore
from core.memory_engine import MemoryEngine
from core.notification_outbox import enqueue_unsent_telegram_notification
from workflows.executive_dashboard import ExecutiveDashboard, build_executive_dashboard


@dataclass(frozen=True)
class DashboardPipelineResult:
    dashboard: ExecutiveDashboard
    brief: BriefRecord
    intelligence_brief: IntelligenceBrief
    notion: DeliveryStatus
    telegram: DeliveryStatus


def run_dashboard_pipeline(
    *,
    store: MemoryStore,
    as_of: str,
    window_start: str,
    notion_url: str,
    notion_client: NotionClient | None = None,
    telegram_client: TelegramClient | None = None,
    model_router: TieredGenerator | None = None,
    publish_notion: bool = False,
    send_telegram: bool = False,
) -> DashboardPipelineResult:
    dashboard = build_executive_dashboard(store, as_of=as_of, window_start=window_start)
    dashboard = type(dashboard)(
        title=dashboard.title,
        executive_summary=synthesize_dashboard_summary(
            title=dashboard.title,
            fallback_summary=dashboard.executive_summary,
            latest_items=tuple(f"{item.label}: {item.title} ({item.status})" for item in dashboard.latest_items),
            top_actions=dashboard.top_actions,
            router=model_router,
        ),
        latest_items=dashboard.latest_items,
        top_actions=dashboard.top_actions,
        delivery_notes=dashboard.delivery_notes,
        operational_health=dashboard.operational_health,
    )
    notion_status = _publish_notion(
        dashboard=dashboard,
        notion_client=notion_client,
        publish_notion=publish_notion,
    )
    notification = _notification(
        dashboard,
        notion_status.detail if notion_status.status == "published" else notion_url,
    )
    telegram_status = _send_telegram(
        notification=notification,
        telegram_client=telegram_client,
        send_telegram=send_telegram,
        notion_status=notion_status,
    )
    enqueue_unsent_telegram_notification(
        store=store,
        notification=notification,
        notion_status=notion_status,
        telegram_status=telegram_status,
        send_telegram=send_telegram,
    )
    brief = store.record_brief(
        brief_type="dashboard",
        domain="AI Intelligence",
        period_start=window_start,
        period_end=as_of,
        title=dashboard.title,
        executive_summary=dashboard.executive_summary,
        top_actions=dashboard.top_actions,
        notion_status=notion_status.status,
        notion_url=notion_status.detail if notion_status.status == "published" else notion_url,
        telegram_status=telegram_status.status,
        telegram_detail=telegram_status.detail,
    )
    intelligence_brief = top_actions_to_intelligence_brief(
        brief_type="dashboard",
        domain="AI Intelligence",
        period_start=window_start,
        period_end=as_of,
        title=dashboard.title,
        executive_summary=dashboard.executive_summary,
        top_actions=dashboard.top_actions,
        synthesis_metadata=SynthesisMetadata(tier="pro" if model_router is not None else "deterministic"),
    )
    MemoryEngine(store).record_synthesis_metadata(
        "brief",
        brief.id,
        intelligence_brief.synthesis_metadata.as_dict(),
    )
    store.record_run(
        run_date=as_of,
        stage="dashboard",
        title=dashboard.title,
        period_start=window_start,
        period_end=as_of,
        status="completed",
        notion_status=notion_status.status,
        notion_url=notion_status.detail if notion_status.status == "published" else notion_url,
        telegram_status=telegram_status.status,
        telegram_detail=telegram_status.detail,
    )
    return DashboardPipelineResult(
        dashboard=dashboard,
        brief=brief,
        intelligence_brief=intelligence_brief,
        notion=notion_status,
        telegram=telegram_status,
    )


def _publish_notion(
    *,
    dashboard: ExecutiveDashboard,
    notion_client: NotionClient | None,
    publish_notion: bool,
) -> DeliveryStatus:
    if not publish_notion:
        return DeliveryStatus(channel="notion", status="dry-run", detail="Notion publishing not requested.")
    if notion_client is None:
        return DeliveryStatus(channel="notion", status="skipped", detail="Missing Notion client.")
    try:
        page: PublishedPage = notion_client.create_page(dashboard.title, _dashboard_body(dashboard))
        return DeliveryStatus(channel="notion", status="published", detail=page.url or page.id)
    except Exception as exc:
        return failed_delivery("notion", exc)


def _notification(dashboard: ExecutiveDashboard, notion_url: str) -> TelegramNotification:
    return TelegramNotification(
        title=dashboard.title,
        decisions=dashboard.top_actions,
        top_action=_top_action(dashboard.top_actions),
        notion_url=notion_url,
        executive_summary=dashboard.executive_summary,
    )


def _send_telegram(
    *,
    notification: TelegramNotification,
    telegram_client: TelegramClient | None,
    send_telegram: bool,
    notion_status: DeliveryStatus,
) -> DeliveryStatus:
    if not send_telegram:
        return DeliveryStatus(channel="telegram", status="dry-run", detail="Telegram send not requested.")
    blocked = telegram_blocked_by_notion(notion_status)
    if blocked is not None:
        return blocked
    if telegram_client is None:
        return DeliveryStatus(channel="telegram", status="skipped", detail="Missing Telegram client.")
    try:
        result: TelegramResult = telegram_client.send_notification(notification)
        return DeliveryStatus(channel="telegram", status="sent", detail=str(result.message_id))
    except Exception as exc:
        return failed_delivery("telegram", exc)


def _dashboard_body(dashboard: ExecutiveDashboard) -> str:
    lines = [dashboard.executive_summary, "", "Latest intelligence:"]
    lines.extend(
        f"- {item.label}: {item.title} ({item.period}) [{item.status}]"
        for item in dashboard.latest_items
    )
    lines.extend(["", "Top actions:"])
    lines.extend(f"- {action}" for action in dashboard.top_actions)
    lines.extend(["", "Delivery:"])
    lines.extend(f"- {note}" for note in dashboard.delivery_notes)
    lines.extend(["", "Operational health:"])
    lines.extend(f"- {item}" for item in dashboard.operational_health)
    return "\n".join(lines)


def _top_action(top_actions: tuple[str, ...]) -> str:
    if not top_actions:
        return "Ignore"
    return top_actions[0].split(":", 1)[0].strip() or "Watch"
