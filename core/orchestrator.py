from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from connectors.github import GitHubClient
from connectors.domain_rss import DomainRssClient
from connectors.notion import NotionClient
from connectors.papers import ArxivClient, PapersWithCodeClient
from connectors.telegram import TelegramClient
from core.dashboard_pipeline import DashboardPipelineResult, run_dashboard_pipeline
from core.daily_pipeline import DailyPipelineResult, run_daily_pipeline
from core.decision_review_pipeline import DecisionReviewPipelineResult, run_decision_review_pipeline
from core.memory import MemoryStore
from core.intelligence_synthesis import TieredGenerator
from core.period_pipeline import PeriodPipelineResult, run_monthly_pipeline
from core.radar_pipeline import RadarPipelineResult, run_radar_pipeline
from core.watchlist import DomainWatchItem, GitHubWatchItem, PaperWatchItem
from core.weekly_pipeline import WeeklyPipelineResult, run_weekly_pipeline
from core.agent_runtime import AgentRegistry, build_default_registry


@dataclass(frozen=True)
class OrchestrationResult:
    daily: DailyPipelineResult
    weekly: WeeklyPipelineResult | None
    monthly: PeriodPipelineResult | None
    dashboard: DashboardPipelineResult | None
    radar: RadarPipelineResult | None
    decision_review: DecisionReviewPipelineResult | None = None


def run_registered_agent(registry: AgentRegistry, agent_id: str, **kwargs):
    return registry.get(agent_id).run(**kwargs)


def run_hermes_orchestration(
    *,
    store: MemoryStore,
    run_date: str,
    github_watchlist: list[GitHubWatchItem],
    paper_watchlist: list[PaperWatchItem],
    domain_watchlist: list[DomainWatchItem] | None = None,
    fixture_root: Path,
    notion_url: str,
    github_client: GitHubClient | None = None,
    paper_client: ArxivClient | PapersWithCodeClient | None = None,
    domain_rss_client: DomainRssClient | None = None,
    github_trending_client = None,
    notion_client: NotionClient | None = None,
    notion_database_id: str | None = None,
    notion_papers_database_id: str | None = None,
    notion_github_repos_database_id: str | None = None,
    notion_ecosystem_database_id: str | None = None,
    notion_decisions_database_id: str | None = None,
    notion_radar_database_id: str | None = None,
    notion_radar_entities_database_id: str | None = None,
    telegram_client: TelegramClient | None = None,
    model_router: TieredGenerator | None = None,
    publish_notion: bool = False,
    send_telegram: bool = False,
    run_weekly: bool = False,
    run_monthly: bool = False,
    run_dashboard: bool = True,
    run_radar: bool = True,
    run_decision_review: bool = False,
    agent_registry: AgentRegistry | None = None,
) -> OrchestrationResult:
    parsed_date = date.fromisoformat(run_date)
    registry = agent_registry or build_default_registry(daily_runner=run_daily_pipeline)
    daily = run_registered_agent(
        registry,
        "ai_intelligence",
        store=store,
        watchlist=github_watchlist,
        paper_watchlist=paper_watchlist,
        domain_watchlist=domain_watchlist or [],
        run_date=run_date,
        revisit_date=(parsed_date + timedelta(days=7)).isoformat(),
        notion_url=notion_url,
        fixture_root=fixture_root,
        github_client=github_client,
        paper_client=paper_client,
        domain_rss_client=domain_rss_client,
        github_trending_client=github_trending_client,
        notion_client=notion_client,
        notion_database_id=notion_database_id,
        notion_papers_database_id=notion_papers_database_id,
        notion_github_repos_database_id=notion_github_repos_database_id,
        notion_ecosystem_database_id=notion_ecosystem_database_id,
        telegram_client=telegram_client,
        model_router=model_router,
        publish_notion=publish_notion,
        send_telegram=send_telegram,
    )

    weekly = None
    if run_weekly:
        week_start = (parsed_date - timedelta(days=parsed_date.weekday())).isoformat()
        week_end = (date.fromisoformat(week_start) + timedelta(days=6)).isoformat()
        weekly = run_weekly_pipeline(
            store=store,
            period_start=week_start,
            period_end=week_end,
            notion_url=notion_url,
            notion_client=notion_client,
            notion_database_id=notion_database_id,
            telegram_client=telegram_client,
            model_router=model_router,
            publish_notion=publish_notion,
            send_telegram=send_telegram,
        )

    monthly = None
    if run_monthly:
        month_start = parsed_date.replace(day=1)
        next_month = month_start.replace(year=month_start.year + 1, month=1) if month_start.month == 12 else month_start.replace(month=month_start.month + 1)
        month_end = next_month - timedelta(days=1)
        monthly = run_monthly_pipeline(
            store=store,
            period_start=month_start.isoformat(),
            period_end=month_end.isoformat(),
            notion_url=notion_url,
            notion_client=notion_client,
            notion_database_id=notion_database_id,
            telegram_client=telegram_client,
            model_router=model_router,
            publish_notion=publish_notion,
            send_telegram=send_telegram,
        )

    dashboard = None
    if run_dashboard:
        dashboard = run_dashboard_pipeline(
            store=store,
            as_of=run_date,
            window_start=(parsed_date - timedelta(days=30)).isoformat(),
            notion_url=notion_url,
            notion_client=notion_client,
            telegram_client=telegram_client,
            model_router=model_router,
            publish_notion=publish_notion,
            send_telegram=send_telegram,
        )

    radar = None
    if run_radar:
        radar = run_radar_pipeline(
            store=store,
            as_of=run_date,
            since=(parsed_date - timedelta(days=30)).isoformat(),
            notion_url=notion_url,
            notion_client=notion_client,
            notion_radar_database_id=notion_radar_database_id,
            notion_radar_entities_database_id=notion_radar_entities_database_id,
            notion_decisions_database_id=notion_decisions_database_id,
            telegram_client=telegram_client,
            publish_notion=publish_notion,
            send_telegram=send_telegram,
        )

    decision_review = None
    if run_decision_review:
        decision_review = run_decision_review_pipeline(
            store=store,
            as_of=run_date,
            since=(parsed_date - timedelta(days=30)).isoformat(),
            notion_url=notion_url,
            notion_client=notion_client,
            notion_database_id=notion_database_id,
            telegram_client=telegram_client,
            publish_notion=publish_notion,
            send_telegram=send_telegram,
        )

    return OrchestrationResult(
        daily=daily,
        weekly=weekly,
        monthly=monthly,
        dashboard=dashboard,
        radar=radar,
        decision_review=decision_review,
    )
