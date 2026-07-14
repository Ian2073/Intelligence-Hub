from __future__ import annotations

from dataclasses import dataclass

from connectors.notion import (
    NotionClient,
    NotionDecisionRecord,
    NotionRadarEntityRecord,
    NotionRadarSnapshotRecord,
    PublishedPage,
)
from connectors.telegram import TelegramClient, TelegramNotification, TelegramResult
from core.delivery import DeliveryStatus, failed_delivery, telegram_blocked_by_notion
from core.intelligence_brief import IntelligenceBrief, top_actions_to_intelligence_brief
from core.memory import BriefRecord, MemoryStore
from core.memory_engine import MemoryEngine
from core.notification_outbox import enqueue_unsent_telegram_notification
from workflows.radar_snapshot import RadarSnapshot, build_radar_snapshot


@dataclass(frozen=True)
class RadarPipelineResult:
    snapshot: RadarSnapshot
    brief: BriefRecord
    intelligence_brief: IntelligenceBrief
    notion: DeliveryStatus
    telegram: DeliveryStatus


def run_radar_pipeline(
    *,
    store: MemoryStore,
    as_of: str,
    since: str | None,
    notion_url: str,
    notion_client: NotionClient | None = None,
    notion_radar_database_id: str | None = None,
    notion_radar_entities_database_id: str | None = None,
    notion_decisions_database_id: str | None = None,
    telegram_client: TelegramClient | None = None,
    publish_notion: bool = False,
    send_telegram: bool = False,
) -> RadarPipelineResult:
    snapshot = build_radar_snapshot(store, as_of=as_of, since=since)
    notion_status = _publish_notion(
        snapshot=snapshot,
        as_of=as_of,
        notion_client=notion_client,
        notion_radar_database_id=notion_radar_database_id,
        notion_radar_entities_database_id=notion_radar_entities_database_id,
        notion_decisions_database_id=notion_decisions_database_id,
        publish_notion=publish_notion,
    )
    notification = _notification(snapshot, notion_status.detail if notion_status.status == "published" else notion_url)
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
        brief_type="radar",
        domain="Executive Intelligence",
        period_start=since or as_of,
        period_end=as_of,
        title=snapshot.title,
        executive_summary=snapshot.executive_summary,
        top_actions=snapshot.top_actions,
        notion_status=notion_status.status,
        notion_url=notion_status.detail if notion_status.status == "published" else notion_url,
        telegram_status=telegram_status.status,
        telegram_detail=telegram_status.detail,
    )
    intelligence_brief = top_actions_to_intelligence_brief(
        brief_type="radar",
        domain="Executive Intelligence",
        period_start=since or as_of,
        period_end=as_of,
        title=snapshot.title,
        executive_summary=snapshot.executive_summary,
        top_actions=snapshot.top_actions,
    )
    MemoryEngine(store).record_synthesis_metadata(
        "brief",
        brief.id,
        intelligence_brief.synthesis_metadata.as_dict(),
    )
    store.record_run(
        run_date=as_of,
        stage="radar",
        title=snapshot.title,
        period_start=since or as_of,
        period_end=as_of,
        status="completed",
        notion_status=notion_status.status,
        notion_url=notion_status.detail if notion_status.status == "published" else notion_url,
        telegram_status=telegram_status.status,
        telegram_detail=telegram_status.detail,
    )
    return RadarPipelineResult(
        snapshot=snapshot,
        brief=brief,
        intelligence_brief=intelligence_brief,
        notion=notion_status,
        telegram=telegram_status,
    )


def _publish_notion(
    *,
    snapshot: RadarSnapshot,
    as_of: str,
    notion_client: NotionClient | None,
    notion_radar_database_id: str | None,
    notion_radar_entities_database_id: str | None,
    notion_decisions_database_id: str | None,
    publish_notion: bool,
) -> DeliveryStatus:
    if not publish_notion:
        return DeliveryStatus(channel="notion", status="dry-run", detail="Notion publishing not requested.")
    if notion_client is None:
        return DeliveryStatus(channel="notion", status="skipped", detail="Missing Notion client.")
    try:
        if notion_radar_database_id:
            page: PublishedPage = notion_client.create_radar_snapshot_record(
                notion_radar_database_id,
                _radar_record(snapshot, as_of),
            )
        else:
            page = notion_client.create_page(snapshot.title, _radar_body(snapshot))

        if notion_radar_entities_database_id:
            for entry in snapshot.entries:
                notion_client.upsert_radar_entity_record(
                    notion_radar_entities_database_id,
                    _radar_entity_record(entry),
                )

        if notion_decisions_database_id:
            for decision in snapshot.decisions:
                notion_client.upsert_decision_record(notion_decisions_database_id, _decision_record(decision))
        return DeliveryStatus(channel="notion", status="published", detail=page.url or page.id)
    except Exception as exc:
        return failed_delivery("notion", exc)


def _notification(snapshot: RadarSnapshot, notion_url: str) -> TelegramNotification:
    return TelegramNotification(
        title=snapshot.title,
        decisions=snapshot.top_actions,
        top_action=_top_action(snapshot.top_actions),
        notion_url=notion_url,
        executive_summary=snapshot.executive_summary,
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


def _radar_body(snapshot: RadarSnapshot) -> str:
    lines = [snapshot.executive_summary, "", "Radar entities:"]
    for entry in snapshot.entries:
        lines.append(f"- [{entry.kind}] {entry.name} ({entry.status}, last seen {entry.last_seen})")
        if entry.summary:
            lines.append(f"  Summary: {entry.summary}")
        if entry.recent_metrics:
            lines.append(f"  Recent metrics: {'; '.join(entry.recent_metrics)}")
        if entry.tags:
            lines.append(f"  Tags: {', '.join(entry.tags)}")
    lines.extend(["", "Top decisions:"])
    lines.extend(f"- {action}" for action in snapshot.top_actions)
    return "\n".join(lines)


def _radar_record(snapshot: RadarSnapshot, as_of: str) -> NotionRadarSnapshotRecord:
    return NotionRadarSnapshotRecord(
        title=snapshot.title,
        as_of=as_of,
        executive_summary=snapshot.executive_summary,
        entity_count=len(snapshot.entries),
        top_actions=_action_names(snapshot.top_actions),
        status="Published",
        body=_radar_body(snapshot),
    )


def _radar_entity_record(entry) -> NotionRadarEntityRecord:
    return NotionRadarEntityRecord(
        name=entry.name,
        type=_entity_type_label(entry.kind),
        status=entry.status,
        last_seen=entry.last_seen,
        summary=entry.summary,
        tags=entry.tags,
        observation_count=entry.observation_count,
        relationship_count=entry.relationship_count,
        recent_metrics=entry.recent_metrics,
    )


def _entity_type_label(kind: str) -> str:
    normalized = kind.strip().casefold().replace("-", "_")
    return {
        "technology": "Technology",
        "company": "Company",
        "company_strategy": "Company",
        "repository": "Repository",
        "paper": "Paper",
        "product": "Product",
        "person": "Person",
        "topic": "Topic",
        "source": "Source",
        "trend": "Trend",
        "concept": "Concept",
    }.get(normalized, "Concept")


def _decision_record(decision) -> NotionDecisionRecord:
    return NotionDecisionRecord(
        title=f"{decision.action}: {decision.signal_id}",
        action=decision.action,
        rationale=decision.rationale,
        expected_payoff=decision.expected_payoff,
        risk=decision.risk,
        revisit_date=decision.revisit_date,
        confidence=decision.confidence,
        signal_id=decision.signal_id,
        status="Open",
    )


def _action_names(top_actions: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(action.split(":", 1)[0].strip() for action in top_actions if action.strip()))


def _top_action(top_actions: tuple[str, ...]) -> str:
    if not top_actions:
        return "Ignore"
    return top_actions[0].split(":", 1)[0].strip() or "Watch"
