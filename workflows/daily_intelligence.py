from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from connectors.github import GitHubRepoSnapshot
from connectors.domain import DomainSignalSnapshot
from connectors.papers import PaperSnapshot
from connectors.telegram import TelegramNotification
from core.cross_signal_analysis import CrossSignalInsight, analyze_cross_signals
from core.decision_engine import ACTION_RANK
from core.domain_radar import DomainRadarResult, ingest_domain_signal_snapshot
from core.github_radar import RepositoryRadarResult, ingest_repository_snapshot
from core.memory import MemoryStore
from core.paper_radar import PaperRadarResult, ingest_paper_snapshot
from core.report_quality import unique_actions


@dataclass(frozen=True)
class DailyIntelligenceRun:
    title: str
    repository_results: tuple[RepositoryRadarResult, ...]
    paper_results: tuple[PaperRadarResult, ...]
    domain_results: tuple[DomainRadarResult, ...]
    notification: TelegramNotification
    cross_signal_insights: tuple[CrossSignalInsight, ...] = ()


def run_daily_intelligence(
    store: MemoryStore,
    repository_snapshots: list[GitHubRepoSnapshot],
    *,
    run_date: str,
    revisit_date: str,
    notion_url: str,
    paper_snapshots: list[PaperSnapshot] | None = None,
    domain_snapshots: list[DomainSignalSnapshot] | None = None,
) -> DailyIntelligenceRun:
    repository_results = tuple(
        ingest_repository_snapshot(store, snapshot, revisit_date=revisit_date)
        for snapshot in sorted(repository_snapshots, key=lambda item: item.stars, reverse=True)
    )
    paper_results = tuple(
        ingest_paper_snapshot(store, snapshot, revisit_date=revisit_date)
        for snapshot in (paper_snapshots or [])
    )
    domain_results = tuple(
        ingest_domain_signal_snapshot(store, snapshot, revisit_date=revisit_date)
        for snapshot in sorted(domain_snapshots or [], key=lambda item: item.impact_score, reverse=True)
    )
    cross_signal_insights = analyze_cross_signals(repository_results, paper_results, domain_results, store)
    top_results = _select_top_results(repository_results, paper_results, domain_results, limit=7)
    decisions = unique_actions(tuple(result.brief_line for result in top_results), limit=7)
    top_action = _top_action(top_results)
    notification = TelegramNotification(
        title=f"Intelligence Hub Daily Intelligence - {run_date}",
        decisions=decisions,
        top_action=top_action,
        notion_url=notion_url,
    )
    return DailyIntelligenceRun(
        title=f"Intelligence Hub Daily Intelligence - {run_date}",
        repository_results=repository_results,
        paper_results=paper_results,
        domain_results=domain_results,
        notification=notification,
        cross_signal_insights=cross_signal_insights,
    )


def run_daily_github_intelligence(
    store: MemoryStore,
    snapshots: list[GitHubRepoSnapshot],
    *,
    run_date: str,
    revisit_date: str,
    notion_url: str,
) -> DailyIntelligenceRun:
    return run_daily_intelligence(
        store,
        snapshots,
        run_date=run_date,
        revisit_date=revisit_date,
        notion_url=notion_url,
    )


def _rank_results(
    repository_results: tuple[RepositoryRadarResult, ...],
    paper_results: tuple[PaperRadarResult, ...],
    domain_results: tuple[DomainRadarResult, ...] = (),
) -> tuple[RepositoryRadarResult | PaperRadarResult | DomainRadarResult, ...]:
    return tuple(
        sorted(
            (*repository_results, *paper_results, *domain_results),
            key=_ranking_key,
        )
    )


def _select_top_results(
    repository_results: tuple[RepositoryRadarResult, ...],
    paper_results: tuple[PaperRadarResult, ...],
    domain_results: tuple[DomainRadarResult, ...] = (),
    *,
    limit: int,
) -> tuple[RepositoryRadarResult | PaperRadarResult | DomainRadarResult, ...]:
    ranked = _rank_results(repository_results, paper_results, domain_results)
    selected = []
    identities = set()
    source_counts: dict[str, int] = {}
    baseline_repo_count = 0
    for result in ranked:
        identity = _decision_identity(result)
        if identity in identities:
            continue
        source = _result_source(result)
        if _is_baseline_repository(result) and baseline_repo_count >= 3:
            continue
        if source_counts.get(source, 0) >= _source_limit(source):
            continue
        selected.append(result)
        identities.add(identity)
        source_counts[source] = source_counts.get(source, 0) + 1
        if _is_baseline_repository(result):
            baseline_repo_count += 1
        if len(selected) >= limit:
            break
    return tuple(selected)


def _top_action(
    top_results: tuple[RepositoryRadarResult | PaperRadarResult | DomainRadarResult, ...],
) -> str:
    if not top_results:
        return "Ignore"
    return top_results[0].decision.action


def _ranking_key(result: RepositoryRadarResult | PaperRadarResult | DomainRadarResult) -> tuple[int, int, int, str]:
    baseline_penalty = 1 if _is_baseline_repository(result) else 0
    return (
        ACTION_RANK.get(result.decision.action, 9),
        baseline_penalty,
        -_signal_strength(result),
        result.entity.canonical_name.casefold(),
    )


def _signal_strength(result: RepositoryRadarResult | PaperRadarResult | DomainRadarResult) -> int:
    if hasattr(result, "priority_score"):
        return int(getattr(result, "priority_score"))
    if hasattr(result, "relationships"):
        return len(getattr(result, "relationships", ())) * 20
    return max(int(getattr(result, "star_delta", 0)), 0)


def _decision_identity(result: RepositoryRadarResult | PaperRadarResult | DomainRadarResult) -> str:
    source = _result_source(result)
    if source == "domain":
        return f"domain:{result.entity.canonical_name.casefold()}"
    if source == "paper":
        return f"paper:{result.entity.canonical_name.casefold()}"
    return f"{source}:{result.entity.canonical_name.casefold()}"


def _result_source(result: Any) -> str:
    signal_id = str(result.decision.signal_id)
    if signal_id.startswith("paper:"):
        return "paper"
    if signal_id.startswith("domain:"):
        return "domain"
    if signal_id.startswith("github-repo:"):
        return "github-repo"
    return signal_id.split(":", 1)[0] or "unknown"


def _source_limit(source: str) -> int:
    if source == "github-repo":
        return 4
    if source == "paper":
        return 4
    if source == "domain":
        return 3
    return 7


def _is_baseline_repository(result: Any) -> bool:
    if _result_source(result) != "github-repo":
        return False
    return int(getattr(result, "star_delta", 0)) == 0
