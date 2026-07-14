from __future__ import annotations

from dataclasses import dataclass

from core.decision_engine import ACTION_RANK
from core.github_radar import RepositoryRadarResult
from core.memory import MemoryStore, Observation
from core.paper_radar import PaperRadarResult
from core.report_quality import build_executive_judgment, unique_actions
from workflows.decision_review import DecisionReviewItem, build_decision_review_report


@dataclass(frozen=True)
class WeeklyTrend:
    name: str
    direction: str
    evidence: str


@dataclass(frozen=True)
class WeeklyIntelligenceReport:
    title: str
    executive_summary: str
    trends: tuple[WeeklyTrend, ...]
    top_actions: tuple[str, ...]
    decision_reviews: tuple[DecisionReviewItem, ...] = ()


def build_weekly_intelligence_report(
    *,
    period_start: str,
    period_end: str,
    repository_results: tuple[RepositoryRadarResult, ...] = (),
    paper_results: tuple[PaperRadarResult, ...] = (),
) -> WeeklyIntelligenceReport:
    trends = _build_trends(repository_results, paper_results)
    top_actions = _top_actions(repository_results, paper_results)
    executive_summary = _summary(repository_results, paper_results, trends)
    return WeeklyIntelligenceReport(
        title=f"Intelligence Hub Weekly Brief - {period_start} to {period_end}",
        executive_summary=executive_summary,
        trends=trends,
        top_actions=top_actions,
    )


def build_weekly_report_from_memory(
    store: MemoryStore,
    *,
    period_start: str,
    period_end: str,
) -> WeeklyIntelligenceReport:
    observations = store.list_observations(since=period_start, until=period_end)
    daily_briefs = store.list_briefs(brief_type="daily", since=period_start, until=period_end)
    decision_review = build_decision_review_report(store, since=period_start, as_of=period_end)
    trends = _memory_trends(observations, daily_briefs, decision_review.items)
    top_actions = unique_actions(tuple(
        dict.fromkeys(
            (
                *(action for brief in daily_briefs for action in brief.top_actions),
                *decision_review.top_actions,
            )
        )
    ), limit=7)
    executive_summary = build_executive_judgment(
        period_label=f"本週（{period_start} 到 {period_end}）",
        top_actions=top_actions,
        trends=tuple((trend.name, trend.direction, trend.evidence) for trend in trends),
        decision_review_count=len(decision_review.items),
    )
    return WeeklyIntelligenceReport(
        title=f"Intelligence Hub Weekly Brief - {period_start} to {period_end}",
        executive_summary=executive_summary,
        trends=trends,
        top_actions=top_actions,
        decision_reviews=decision_review.items,
    )


def _build_trends(
    repository_results: tuple[RepositoryRadarResult, ...],
    paper_results: tuple[PaperRadarResult, ...],
) -> tuple[WeeklyTrend, ...]:
    repo_delta = sum(result.star_delta for result in repository_results)
    prototype_count = sum(
        1
        for result in (*repository_results, *paper_results)
        if result.decision.action == "Prototype"
    )
    trends = [
        WeeklyTrend(
            name="Open-source AI engineering",
            direction="Up" if repo_delta >= 500 else "Stable",
            evidence=f"Tracked repositories changed by {repo_delta:+d} stars.",
        ),
        WeeklyTrend(
            name="Research-to-implementation",
            direction="Up" if prototype_count else "Watch",
            evidence=f"{prototype_count} signals reached Prototype action.",
        ),
    ]
    return tuple(trends)


def _top_actions(
    repository_results: tuple[RepositoryRadarResult, ...],
    paper_results: tuple[PaperRadarResult, ...],
) -> tuple[str, ...]:
    rows = [
        (result.decision.action, result.brief_line)
        for result in (*repository_results, *paper_results)
    ]
    ranked = sorted(rows, key=lambda row: ACTION_RANK.get(row[0], 9))
    return unique_actions(tuple(row[1] for row in ranked), limit=5)


def _summary(
    repository_results: tuple[RepositoryRadarResult, ...],
    paper_results: tuple[PaperRadarResult, ...],
    trends: tuple[WeeklyTrend, ...],
) -> str:
    up_trends = ", ".join(trend.name for trend in trends if trend.direction == "Up") or "none"
    return (
        f"本週判斷：{up_trends} 是主要升溫方向。"
        f"最高價值訊號來自 {len(repository_results)} 個 repository 和 {len(paper_results)} 篇 paper；"
        "只升級需要閱讀或原型驗證的項目。"
    )


def _memory_trends(
    observations: list[Observation],
    daily_briefs,
    decision_reviews: tuple[DecisionReviewItem, ...] = (),
) -> tuple[WeeklyTrend, ...]:
    star_delta = 0
    paper_count = 0
    for observation in observations:
        if observation.metric_name == "stars":
            try:
                star_delta += int(observation.current_value) - int(observation.previous_value)
            except ValueError:
                pass
        if observation.source_type == "paper":
            paper_count += 1

    prototype_count = sum(
        1
        for brief in daily_briefs
        for action in brief.top_actions
        if action.startswith("Prototype:")
    )
    trends = [
        WeeklyTrend(
            name="Open-source AI engineering",
            direction="Up" if star_delta >= 500 else "Stable",
            evidence=f"Repository star delta from memory: {star_delta:+d}.",
        ),
        WeeklyTrend(
            name="Research-to-implementation",
            direction="Up" if prototype_count or paper_count else "Watch",
            evidence=f"{paper_count} paper observations and {prototype_count} prototype actions from daily briefs.",
        ),
    ]
    if decision_reviews:
        trends.append(
            WeeklyTrend(
                name="Decision quality",
                direction="Review",
                evidence=f"{len(decision_reviews)} prior decisions reached their revisit date.",
            )
        )
    return tuple(trends)
