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
from core.dashboard_pipeline import run_dashboard_pipeline
from core.memory import MemoryStore
from core.model_router import ModelRouter


def parse_args() -> argparse.Namespace:
    today = date.today()
    parser = argparse.ArgumentParser(description="Build Hermes executive dashboard from memory.")
    parser.add_argument("--as-of", default=today.isoformat(), help="Dashboard date in YYYY-MM-DD format.")
    parser.add_argument(
        "--window-start",
        default=(today - timedelta(days=30)).isoformat(),
        help="Start date for dashboard memory window.",
    )
    parser.add_argument("--publish-notion", action="store_true", help="Publish dashboard page to Notion.")
    parser.add_argument("--send-telegram", action="store_true", help="Send Telegram dashboard notification.")
    parser.add_argument("--model-synthesis", action="store_true", help="Use configured pro model for executive summary synthesis.")
    parser.add_argument("--notion-url", default="local://notion/dashboard-dry-run", help="Fallback Notion URL.")
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
        if not settings.notion_token or not settings.notion_parent_page_id:
            print("Notion dashboard publishing skipped: NOTION_TOKEN and NOTION_PARENT_PAGE_ID are required.")
        else:
            notion_client = NotionClient(settings.notion_token, settings.notion_parent_page_id)

    telegram_client = None
    if args.send_telegram:
        if not settings.telegram_enabled:
            print("Telegram send skipped: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not both set.")
        else:
            telegram_client = TelegramClient(settings.telegram_bot_token or "", settings.telegram_chat_id or "")
    model_router = ModelRouter(settings) if args.model_synthesis else None

    store = MemoryStore(settings.memory_db)
    try:
        result = run_dashboard_pipeline(
            store=store,
            as_of=args.as_of,
            window_start=args.window_start,
            notion_url=args.notion_url,
            notion_client=notion_client,
            telegram_client=telegram_client,
            model_router=model_router,
            publish_notion=args.publish_notion,
            send_telegram=args.send_telegram,
        )
    except Exception as exc:
        send_pipeline_alert(
            store=store,
            pipeline="dashboard",
            error=exc,
            settings=settings,
            telegram_client=telegram_client,
        )
        print(f"Executive dashboard run failed: {exc}")
        return 1
    finally:
        store.close()

    dashboard = result.dashboard
    print(dashboard.title)
    print(dashboard.executive_summary)
    print("Latest intelligence:")
    for item in dashboard.latest_items:
        print(f"- {item.label}: {item.title} ({item.period}) [{item.status}]")
    print("Top actions:")
    if dashboard.top_actions:
        for action in dashboard.top_actions:
            print(f"- {action}")
    else:
        print("- No top actions found in memory.")
    print(f"Notion: {result.notion.status} - {result.notion.detail}")
    print(f"Telegram: {result.telegram.status} - {result.telegram.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
