from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from connectors.github import GitHubClient
from connectors.github_trending import GitHubTrendingClient
from connectors.domain_rss import DomainRssClient
from connectors.notion import NotionClient
from connectors.papers import ArxivClient, PapersWithCodeClient
from connectors.telegram import TelegramClient
from core.alerting import send_pipeline_alert
from core.config import load_settings
from core.memory import MemoryStore
from core.model_router import ModelRouter
from core.orchestrator import run_hermes_orchestration
from core.runtime_safety import validate_memory_target_for_run
from core.watchlist import load_domain_watchlist, load_github_watchlist, load_paper_watchlist


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Hermes Intelligence OS orchestration.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Run date in YYYY-MM-DD format.")
    parser.add_argument("--live-github", action="store_true", help="Fetch GitHub live instead of fixture data.")
    parser.add_argument("--live-papers", action="store_true", help="Fetch papers from arXiv instead of fixture data.")
    parser.add_argument("--live-papers-with-code", action="store_true", help="Fetch papers from Papers with Code instead of fixture data.")
    parser.add_argument("--live-domain-rss", action="store_true", help="Fetch domain signals from RSS feeds instead of fixture data where rss_url is configured.")
    parser.add_argument("--publish-notion", action="store_true", help="Publish Notion outputs.")
    parser.add_argument("--send-telegram", action="store_true", help="Send Telegram notifications.")
    parser.add_argument("--model-synthesis", action="store_true", help="Use configured pro model for daily/weekly executive synthesis.")
    parser.add_argument("--weekly", action="store_true", help="Also run weekly report for the run date week.")
    parser.add_argument("--monthly", action="store_true", help="Also run monthly report for the run date month.")
    parser.add_argument("--no-dashboard", action="store_true", help="Skip Executive Dashboard generation.")
    parser.add_argument("--no-radar", action="store_true", help="Skip Radar Snapshot generation.")
    parser.add_argument("--decision-review", action="store_true", help="Also run decision review.")
    parser.add_argument("--notion-url", default="local://notion/orchestration-dry-run", help="Fallback Notion URL.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _model_synthesis_enabled(settings, requested: bool) -> bool:
    return requested or settings.synthesis_mode in {"hybrid", "full"}


def main() -> int:
    configure_stdout()
    args = parse_args()
    settings = load_settings(PROJECT_ROOT)
    safety_error = validate_memory_target_for_run(
        settings,
        publish_notion=args.publish_notion,
        notion_url=args.notion_url,
        operation="Hermes orchestration",
    )
    if safety_error:
        print(safety_error)
        return 1
    github_watchlist = load_github_watchlist(settings.github_watchlist_file)
    paper_watchlist = load_paper_watchlist(settings.paper_watchlist_file)
    domain_watchlist = load_domain_watchlist(settings.domain_watchlist_file)
    if not github_watchlist and not paper_watchlist and not domain_watchlist:
        print("No watchlist items configured.")
        return 1

    if args.live_papers and args.live_papers_with_code:
        print("Choose only one paper live source: --live-papers or --live-papers-with-code.")
        return 1
    github_client = GitHubClient(settings.github_token) if args.live_github else None
    github_trending_client = GitHubTrendingClient(settings.github_token) if args.live_github else None
    paper_client = None
    if args.live_papers:
        paper_client = ArxivClient()
    if args.live_papers_with_code:
        paper_client = PapersWithCodeClient()
    domain_rss_client = DomainRssClient() if args.live_domain_rss else None
    notion_client = None
    if args.publish_notion:
        if not settings.notion_token or not settings.notion_parent_page_id:
            print("Notion publishing skipped: NOTION_TOKEN and NOTION_PARENT_PAGE_ID are required.")
        else:
            notion_client = NotionClient(settings.notion_token, settings.notion_parent_page_id)
    telegram_client = None
    if args.send_telegram:
        if not settings.telegram_enabled:
            print("Telegram send skipped: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not both set.")
        else:
            telegram_client = TelegramClient(settings.telegram_bot_token or "", settings.telegram_chat_id or "")
    model_router = ModelRouter(settings) if _model_synthesis_enabled(settings, args.model_synthesis) else None

    store = MemoryStore(settings.memory_db)
    try:
        result = run_hermes_orchestration(
            store=store,
            run_date=args.date,
            github_watchlist=github_watchlist,
            paper_watchlist=paper_watchlist,
            domain_watchlist=domain_watchlist,
            fixture_root=settings.fixture_root,
            notion_url=args.notion_url,
            github_client=github_client,
            paper_client=paper_client,
            domain_rss_client=domain_rss_client,
            github_trending_client=github_trending_client,
            notion_client=notion_client,
            notion_database_id=settings.notion_daily_briefs_database_id,
            notion_papers_database_id=settings.notion_papers_database_id,
            notion_github_repos_database_id=settings.notion_github_repos_database_id,
            notion_ecosystem_database_id=settings.notion_ecosystem_database_id,
            notion_decisions_database_id=settings.notion_decisions_database_id,
            notion_radar_database_id=settings.notion_radar_snapshots_database_id,
            notion_radar_entities_database_id=settings.notion_radar_entities_database_id,
            telegram_client=telegram_client,
            model_router=model_router,
            publish_notion=args.publish_notion,
            send_telegram=args.send_telegram,
            run_weekly=args.weekly,
            run_monthly=args.monthly,
            run_dashboard=not args.no_dashboard,
            run_radar=not args.no_radar,
            run_decision_review=args.decision_review,
        )
    except Exception as exc:
        send_pipeline_alert(
            store=store,
            pipeline="orchestration",
            error=exc,
            settings=settings,
            telegram_client=telegram_client,
        )
        print(f"Hermes orchestration failed: {exc}")
        return 1
    finally:
        store.close()

    print(f"Daily: {result.daily.run.title}")
    print(f"Daily Notion: {result.daily.notion.status}; Telegram: {result.daily.telegram.status}")
    if result.weekly:
        print(f"Weekly: {result.weekly.report.title}")
        print(f"Weekly Notion: {result.weekly.notion.status}; Telegram: {result.weekly.telegram.status}")
    if result.monthly:
        print(f"Monthly: {result.monthly.report.title}")
        print(f"Monthly Notion: {result.monthly.notion.status}; Telegram: {result.monthly.telegram.status}")
    if result.dashboard:
        print(f"Dashboard: {result.dashboard.dashboard.title}")
        print(f"Dashboard Notion: {result.dashboard.notion.status}; Telegram: {result.dashboard.telegram.status}")
    if result.radar:
        print(f"Radar: {result.radar.snapshot.title}")
        print(f"Radar Notion: {result.radar.notion.status}; Telegram: {result.radar.telegram.status}")
    if result.decision_review:
        print(f"Decision Review: {result.decision_review.report.title}")
        print(
            "Decision Review Notion: "
            f"{result.decision_review.notion.status}; Telegram: {result.decision_review.telegram.status}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
