from __future__ import annotations

from dataclasses import dataclass

from connectors.notion import NotionBriefRecord, NotionClient
from connectors.telegram import TelegramClient, TelegramNotification, TelegramResult
from core.delivery import (
    BriefDeliveryCoordinator,
    DeliveryStatus,
    TelegramBriefRenderer,
    TelegramNotificationPublisher,
    failed_delivery,
    telegram_blocked_by_notion,
)
from core.intelligence_brief import IntelligenceBrief, top_actions_to_intelligence_brief
from core.memory import BriefRecord, MemoryStore
from core.memory_engine import MemoryEngine
from core.notification_outbox import enqueue_unsent_telegram_notification
from workflows.decision_review import DecisionReviewReport, build_decision_review_report


@dataclass(frozen=True)
class DecisionReviewPipelineResult:
    report: DecisionReviewReport
    brief: BriefRecord
    intelligence_brief: IntelligenceBrief
    notion: DeliveryStatus
    telegram: DeliveryStatus


def run_decision_review_pipeline(
    *,
    store: MemoryStore,
    as_of: str,
    since: str | None,
    notion_url: str,
    notion_client: NotionClient | None = None,
    notion_database_id: str | None = None,
    telegram_client: TelegramClient | None = None,
    publish_notion: bool = False,
    send_telegram: bool = False,
) -> DecisionReviewPipelineResult:
    report = build_decision_review_report(store, as_of=as_of, since=since)
    notion_status = _publish_notion(
        report=report,
        as_of=as_of,
        notion_client=notion_client,
        notion_database_id=notion_database_id,
        publish_notion=publish_notion,
    )
    notification = _notification(report, notion_status.detail if notion_status.status == "published" else notion_url)
    intelligence_brief = top_actions_to_intelligence_brief(
        brief_type="decision_review",
        domain="AI Intelligence",
        period_start=since or as_of,
        period_end=as_of,
        title=report.title,
        executive_summary=report.executive_summary,
        top_actions=report.top_actions,
    )
    telegram_status = _send_telegram(
        notification=notification,
        intelligence_brief=intelligence_brief,
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
        brief_type="decision_review",
        domain="AI Intelligence",
        period_start=since or as_of,
        period_end=as_of,
        title=report.title,
        executive_summary=report.executive_summary,
        top_actions=report.top_actions,
        notion_status=notion_status.status,
        notion_url=notion_status.detail if notion_status.status == "published" else notion_url,
        telegram_status=telegram_status.status,
        telegram_detail=telegram_status.detail,
    )
    MemoryEngine(store).record_synthesis_metadata(
        "brief",
        brief.id,
        intelligence_brief.synthesis_metadata.as_dict(),
    )
    store.record_run(
        run_date=as_of,
        stage="decision_review",
        title=report.title,
        period_start=since or as_of,
        period_end=as_of,
        status="completed",
        notion_status=notion_status.status,
        notion_url=notion_status.detail if notion_status.status == "published" else notion_url,
        telegram_status=telegram_status.status,
        telegram_detail=telegram_status.detail,
    )
    return DecisionReviewPipelineResult(
        report=report,
        brief=brief,
        intelligence_brief=intelligence_brief,
        notion=notion_status,
        telegram=telegram_status,
    )


def _publish_notion(
    *,
    report: DecisionReviewReport,
    as_of: str,
    notion_client: NotionClient | None,
    notion_database_id: str | None,
    publish_notion: bool,
) -> DeliveryStatus:
    if not publish_notion:
        return DeliveryStatus(channel="notion", status="dry-run", detail="Notion publishing not requested.")
    if notion_client is None or not notion_database_id:
        return DeliveryStatus(channel="notion", status="skipped", detail="Missing Notion client or database id.")
    try:
        page = notion_client.create_brief_record(notion_database_id, _brief_record(report, as_of))
        return DeliveryStatus(channel="notion", status="published", detail=page.url or page.id)
    except Exception as exc:
        return failed_delivery("notion", exc)


def _brief_record(report: DecisionReviewReport, as_of: str) -> NotionBriefRecord:
    body_lines = [report.executive_summary, "", "Decision reviews:"]
    if report.items:
        body_lines.extend(
            (
                f"- {item.original_action} / {item.signal_id}: {item.review_status} "
                f"since {item.revisit_date}; payoff={item.expected_payoff}; risk={item.risk}"
            )
            for item in report.items
        )
    else:
        body_lines.append("- No decisions are due.")
    body_lines.extend(["", "Top actions:"])
    body_lines.extend(f"- {action}" for action in report.top_actions)
    return NotionBriefRecord(
        title=report.title,
        date=as_of,
        executive_summary=report.executive_summary,
        recommended_actions=_recommended_actions(report.top_actions),
        intelligence_score=_score(report),
        confidence="medium" if report.items else "low",
        status="Published",
        tags=("AI Intelligence", "Decision Review"),
        body="\n".join(body_lines),
    )


def _notification(report: DecisionReviewReport, notion_url: str) -> TelegramNotification:
    return TelegramNotification(
        title=report.title,
        decisions=report.top_actions,
        top_action=_top_action(report.top_actions),
        notion_url=notion_url,
        executive_summary=report.executive_summary,
    )


def _send_telegram(
    *,
    notification: TelegramNotification,
    intelligence_brief: IntelligenceBrief,
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
        coordinator = BriefDeliveryCoordinator(
            renderers={"telegram": TelegramBriefRenderer()},
            publishers={"telegram": TelegramNotificationPublisher(telegram_client, notification)},
        )
        return coordinator.deliver(intelligence_brief, requested=("telegram",))[0]
    except Exception as exc:
        return failed_delivery("telegram", exc)


def _recommended_actions(top_actions: tuple[str, ...]) -> tuple[str, ...]:
    actions = []
    for line in top_actions:
        action = line.split(":", 1)[0].strip()
        if action and action not in actions:
            actions.append(action)
    return tuple(actions)


def _top_action(top_actions: tuple[str, ...]) -> str:
    if not top_actions:
        return "Ignore"
    return top_actions[0].split(":", 1)[0].strip() or "Review later"


def _score(report: DecisionReviewReport) -> int:
    if not report.items:
        return 35
    overdue = sum(1 for item in report.items if item.review_status == "overdue")
    return min(90, 60 + overdue * 5 + len(report.items) * 3)
