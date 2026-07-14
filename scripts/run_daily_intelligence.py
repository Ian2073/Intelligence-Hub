from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from connectors.github import GitHubClient
from connectors.github_trending import GitHubTrendingClient
from connectors.domain_rss import DomainRssClient
from connectors.notion import NotionClient
from connectors.obsidian import ObsidianClient
from connectors.papers import ArxivClient, PapersWithCodeClient
from connectors.telegram import TelegramClient
from core.alerting import send_pipeline_alert
from core.config import load_settings
from core.daily_pipeline import run_daily_pipeline
from core.memory import MemoryStore
from core.model_router import ModelRouter
from core.runtime_safety import validate_memory_target_for_run
from core.watchlist import load_domain_watchlist, load_github_watchlist, load_paper_watchlist


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Intelligence Hub daily intelligence pipeline.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Run date in YYYY-MM-DD format.")
    parser.add_argument("--revisit-date", help="Decision revisit date in YYYY-MM-DD format.")
    parser.add_argument("--live-github", action="store_true", help="Fetch GitHub live instead of fixture data.")
    parser.add_argument("--live-papers", action="store_true", help="Fetch papers from arXiv instead of fixture data.")
    parser.add_argument("--live-papers-with-code", action="store_true", help="Fetch papers from Papers with Code instead of fixture data.")
    parser.add_argument("--live-domain-rss", action="store_true", help="Fetch domain signals from RSS feeds instead of fixture data where rss_url is configured.")
    parser.add_argument("--publish-notion", action="store_true", help="Publish structured brief to Notion.")
    parser.add_argument("--publish-obsidian", action="store_true", help="Publish structured brief to Obsidian.")
    parser.add_argument("--send-telegram", action="store_true", help="Send Telegram notification.")
    parser.add_argument("--model-synthesis", action="store_true", help="Use configured pro model for executive summary synthesis.")
    parser.add_argument("--notion-url", default="local://notion/dry-run", help="Fallback Notion URL for dry runs.")
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
        operation="Daily intelligence",
    )
    if safety_error:
        print(safety_error)
        return 1
    revisit_date = args.revisit_date or (date.fromisoformat(args.date) + timedelta(days=7)).isoformat()
    watchlist = load_github_watchlist(settings.github_watchlist_file)
    paper_watchlist = load_paper_watchlist(settings.paper_watchlist_file)
    domain_watchlist = load_domain_watchlist(settings.domain_watchlist_file)
    if not watchlist and not paper_watchlist and not domain_watchlist:
        print(
            "No watchlist items found: "
            f"{settings.github_watchlist_file}; {settings.paper_watchlist_file}; {settings.domain_watchlist_file}"
        )
        return 1

    github_client = GitHubClient(token=settings.github_token) if args.live_github else None
    github_trending_client = GitHubTrendingClient(token=settings.github_token) if args.live_github else None
    if args.live_papers and args.live_papers_with_code:
        print("Choose only one paper live source: --live-papers or --live-papers-with-code.")
        return 1
    paper_client = None
    if args.live_papers:
        paper_client = ArxivClient()
    if args.live_papers_with_code:
        paper_client = PapersWithCodeClient()
    domain_rss_client = DomainRssClient() if args.live_domain_rss else None
    fixture_root = settings.fixture_root
    notion_client = None
    if args.publish_notion:
        if not settings.notion_token:
            print("Notion publishing skipped: NOTION_TOKEN is missing.")
        else:
            notion_client = NotionClient(token=settings.notion_token, parent_page_id=settings.notion_parent_page_id or "")

    obsidian_client = None
    if args.publish_obsidian:
        if not settings.obsidian_enabled:
            print("Obsidian publishing skipped: OBSIDIAN_ENABLED is false or OBSIDIAN_VAULT_PATH is missing.")
        else:
            obsidian_client = ObsidianClient(vault_path=settings.obsidian_vault_path or "")

    telegram_client = None
    if args.send_telegram:
        if not settings.telegram_enabled:
            print("Telegram send skipped: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not both set.")
        else:
            telegram_client = TelegramClient(
                bot_token=settings.telegram_bot_token or "",
                chat_id=settings.telegram_chat_id or "",
            )
    model_router = ModelRouter(settings) if _model_synthesis_enabled(settings, args.model_synthesis) else None

    store = MemoryStore(settings.memory_db)
    try:
        result = run_daily_pipeline(
            store=store,
            watchlist=watchlist,
            paper_watchlist=paper_watchlist,
            domain_watchlist=domain_watchlist,
            run_date=args.date,
            revisit_date=revisit_date,
            notion_url=args.notion_url,
            fixture_root=fixture_root,
            github_client=github_client,
            paper_client=paper_client,
            domain_rss_client=domain_rss_client,
            github_trending_client=github_trending_client,
            notion_client=notion_client,
            notion_database_id=settings.notion_daily_briefs_database_id,
            notion_papers_database_id=settings.notion_papers_database_id,
            notion_github_repos_database_id=settings.notion_github_repos_database_id,
            notion_ecosystem_database_id=settings.notion_ecosystem_database_id,
            telegram_client=telegram_client,
            model_router=model_router,
            publish_notion=args.publish_notion,
            send_telegram=args.send_telegram,
            obsidian_client=obsidian_client,
            publish_obsidian=args.publish_obsidian,
        )
    except Exception as exc:
        send_pipeline_alert(
            store=store,
            pipeline="daily",
            error=exc,
            settings=settings,
            telegram_client=telegram_client,
        )
        print(f"Daily intelligence run failed: {exc}")
        return 1
    finally:
        store.close()

    print(result.run.title)
    print(f"Repositories processed: {len(result.run.repository_results)}")
    print(f"Papers processed: {len(result.run.paper_results)}")
    print(f"Domain signals processed: {len(result.run.domain_results)}")
    for line in result.run.notification.decisions:
        print(f"- {line}")
    print(f"Notion: {result.notion.status} - {result.notion.detail}")
    for status in result.structured_notion:
        print(f"{status.channel}: {status.status} - {status.detail}")
    print(f"Telegram: {result.telegram.status} - {result.telegram.detail}")
    if result.obsidian:
        print(f"Obsidian: {result.obsidian.status} - {result.obsidian.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
