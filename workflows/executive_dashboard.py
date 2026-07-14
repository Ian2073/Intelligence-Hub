from __future__ import annotations

from dataclasses import dataclass

from core.memory import BriefRecord, MemoryStore
from core.operational_status import get_health_metrics, render_health_metrics
from core.report_quality import build_executive_judgment, unique_actions


@dataclass(frozen=True)
class DashboardItem:
    label: str
    title: str
    period: str
    status: str
    url: str


@dataclass(frozen=True)
class ExecutiveDashboard:
    title: str
    executive_summary: str
    latest_items: tuple[DashboardItem, ...]
    top_actions: tuple[str, ...]
    delivery_notes: tuple[str, ...]
    operational_health: tuple[str, ...]


def build_executive_dashboard(
    store: MemoryStore,
    *,
    as_of: str,
    window_start: str,
) -> ExecutiveDashboard:
    daily = _latest_brief(store, "daily", since=window_start, until=as_of)
    weekly = _latest_brief(store, "weekly", since=window_start, until=as_of)
    monthly = _latest_brief(store, "monthly", since=window_start, until=as_of)
    latest = tuple(item for item in (daily, weekly, monthly) if item is not None)
    top_actions = unique_actions(tuple(action for brief in latest for action in brief.top_actions), limit=7)
    latest_items = tuple(_dashboard_item(brief) for brief in latest)
    delivery_notes = tuple(_delivery_note(brief) for brief in latest)
    operational_health = render_health_metrics(get_health_metrics(store, since=window_start, until=as_of))
    executive_summary = (
        build_executive_judgment(
            period_label=f"Dashboard {as_of}",
            top_actions=top_actions,
        )
        + f" Operational health: {operational_health[0].removeprefix('Pipeline runs: ')}"
    )
    return ExecutiveDashboard(
        title=f"Intelligence Hub Executive Dashboard - {as_of}",
        executive_summary=executive_summary,
        latest_items=latest_items,
        top_actions=top_actions,
        delivery_notes=delivery_notes,
        operational_health=operational_health,
    )


def _latest_brief(
    store: MemoryStore,
    brief_type: str,
    *,
    since: str,
    until: str,
) -> BriefRecord | None:
    briefs = store.list_briefs(brief_type=brief_type, since=since, until=until)
    if not briefs:
        return None
    return sorted(
        briefs,
        key=lambda item: (
            item.period_end,
            item.period_start,
            _delivery_rank(item.notion_status),
            item.id,
        ),
        reverse=True,
    )[0]


def _delivery_rank(status: str) -> int:
    return {
        "published": 3,
        "sent": 3,
        "dry-run": 2,
        "skipped": 1,
        "failed": 0,
    }.get(status, 0)


def _dashboard_item(brief: BriefRecord) -> DashboardItem:
    return DashboardItem(
        label=brief.brief_type.title(),
        title=brief.title,
        period=f"{brief.period_start} to {brief.period_end}",
        status=f"Notion={brief.notion_status}, Telegram={brief.telegram_status}",
        url=brief.notion_url,
    )


def _delivery_note(brief: BriefRecord) -> str:
    return (
        f"{brief.brief_type}: Notion {brief.notion_status}"
        f"{f' ({brief.notion_url})' if brief.notion_url else ''}; "
        f"Telegram {brief.telegram_status}"
        f"{f' ({brief.telegram_detail})' if brief.telegram_detail else ''}"
    )
