from __future__ import annotations

from dataclasses import dataclass

from core.memory import BriefRecord, MemoryStore, Observation
from core.report_quality import build_executive_judgment, unique_actions


@dataclass(frozen=True)
class PeriodTrend:
    name: str
    direction: str
    evidence: str


@dataclass(frozen=True)
class PeriodIntelligenceReport:
    brief_type: str
    title: str
    executive_summary: str
    trends: tuple[PeriodTrend, ...]
    top_actions: tuple[str, ...]


def build_monthly_report_from_memory(
    store: MemoryStore,
    *,
    period_start: str,
    period_end: str,
) -> PeriodIntelligenceReport:
    observations = store.list_observations(since=period_start, until=period_end)
    daily_briefs = store.list_briefs(brief_type="daily", since=period_start, until=period_end)
    weekly_briefs = store.list_briefs(brief_type="weekly", since=period_start, until=period_end)
    source_briefs = (*weekly_briefs, *daily_briefs)
    trends = _period_trends(observations, source_briefs)
    top_actions = unique_actions(tuple(dict.fromkeys(action for brief in source_briefs for action in brief.top_actions)), limit=7)
    executive_summary = build_executive_judgment(
        period_label=f"本月（{period_start} 到 {period_end}）",
        top_actions=top_actions,
        trends=tuple((trend.name, trend.direction, trend.evidence) for trend in trends),
    )
    return PeriodIntelligenceReport(
        brief_type="monthly",
        title=f"Intelligence Hub Monthly Brief - {period_start} to {period_end}",
        executive_summary=executive_summary,
        trends=trends,
        top_actions=top_actions,
    )


def _period_trends(
    observations: list[Observation],
    briefs: tuple[BriefRecord, ...],
) -> tuple[PeriodTrend, ...]:
    star_delta = _star_delta(observations)
    paper_count = sum(1 for observation in observations if observation.source_type == "paper")
    prototype_count = sum(
        1
        for brief in briefs
        for action in brief.top_actions
        if action.startswith("Prototype:")
    )
    watch_count = sum(
        1
        for brief in briefs
        for action in brief.top_actions
        if action.startswith("Watch:")
    )
    return (
        PeriodTrend(
            name="Open-source AI engineering",
            direction="Up" if star_delta >= 1500 else "Stable",
            evidence=f"Repository star delta from memory: {star_delta:+d}.",
        ),
        PeriodTrend(
            name="Research-to-implementation",
            direction="Up" if prototype_count or paper_count >= 3 else "Watch",
            evidence=f"{paper_count} paper observations and {prototype_count} prototype actions across briefs.",
        ),
        PeriodTrend(
            name="Watchlist pressure",
            direction="Up" if watch_count >= 3 else "Stable",
            evidence=f"{watch_count} watch actions remained unresolved in period briefs.",
        ),
    )


def _star_delta(observations: list[Observation]) -> int:
    total = 0
    for observation in observations:
        if observation.metric_name != "stars":
            continue
        try:
            total += int(observation.current_value) - int(observation.previous_value)
        except ValueError:
            continue
    return total
