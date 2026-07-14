from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from connectors.notion import NotionClient
from connectors.telegram import TelegramClient
from core.alerting import send_pipeline_alert
from core.config import load_settings
from core.memory import MemoryStore
from core.model_router import ModelRouter
from core.weekly_pipeline import run_weekly_pipeline


def parse_args() -> argparse.Namespace:
    default_end = date.today()
    default_start = default_end - timedelta(days=6)
    parser = argparse.ArgumentParser(description="Build the Intelligence Hub weekly intelligence report from memory.")
    parser.add_argument("--start", default=default_start.isoformat(), help="Period start in YYYY-MM-DD format.")
    parser.add_argument("--end", default=default_end.isoformat(), help="Period end in YYYY-MM-DD format.")
    parser.add_argument("--publish-notion", action="store_true", help="Publish structured weekly brief to Notion.")
    parser.add_argument("--send-telegram", action="store_true", help="Send Telegram weekly notification.")
    parser.add_argument("--model-synthesis", action="store_true", help="Use configured pro model for executive summary synthesis.")
    parser.add_argument("--notion-url", default="local://notion/weekly-dry-run", help="Fallback Notion URL for dry runs.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdout()
    args = parse_args()
    settings = load_settings(PROJECT_ROOT)
    notion_client = None
    if args.publish_notion:
        if not settings.notion_token:
            print("Notion publishing skipped: NOTION_TOKEN is missing.")
        else:
            notion_client = NotionClient(token=settings.notion_token, parent_page_id=settings.notion_parent_page_id or "")

    telegram_client = None
    if args.send_telegram:
        if not settings.telegram_enabled:
            print("Telegram send skipped: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not both set.")
        else:
            telegram_client = TelegramClient(
                bot_token=settings.telegram_bot_token or "",
                chat_id=settings.telegram_chat_id or "",
            )
    model_router = ModelRouter(settings) if args.model_synthesis else None

    store = MemoryStore(settings.memory_db)
    try:
        result = run_weekly_pipeline(
            store=store,
            period_start=args.start,
            period_end=args.end,
            notion_url=args.notion_url,
            notion_client=notion_client,
            notion_database_id=settings.notion_daily_briefs_database_id,
            telegram_client=telegram_client,
            model_router=model_router,
            publish_notion=args.publish_notion,
            send_telegram=args.send_telegram,
        )
    except Exception as exc:
        send_pipeline_alert(
            store=store,
            pipeline="weekly",
            error=exc,
            settings=settings,
            telegram_client=telegram_client,
        )
        print(f"Weekly intelligence run failed: {exc}")
        return 1
    finally:
        store.close()

    report = result.report
    print(report.title)
    print(report.executive_summary)
    print("Trends:")
    for trend in report.trends:
        print(f"- {trend.name}: {trend.direction} ({trend.evidence})")
    print("Top actions:")
    if report.top_actions:
        for action in report.top_actions:
            print(f"- {action}")
    else:
        print("- No top actions found in memory.")
    print(f"Notion: {result.notion.status} - {result.notion.detail}")
    print(f"Telegram: {result.telegram.status} - {result.telegram.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
