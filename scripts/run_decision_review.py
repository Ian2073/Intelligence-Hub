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
from core.decision_review_pipeline import run_decision_review_pipeline
from core.memory import MemoryStore


def parse_args() -> argparse.Namespace:
    default_as_of = date.today()
    default_since = default_as_of - timedelta(days=30)
    parser = argparse.ArgumentParser(description="Review due Intelligence Hub decisions from memory.")
    parser.add_argument("--as-of", default=default_as_of.isoformat(), help="Review date in YYYY-MM-DD format.")
    parser.add_argument("--since", default=default_since.isoformat(), help="Earliest revisit date to include.")
    parser.add_argument("--publish-notion", action="store_true", help="Publish structured decision review to Notion.")
    parser.add_argument("--send-telegram", action="store_true", help="Send Telegram decision review notification.")
    parser.add_argument("--notion-url", default="local://notion/decision-review-dry-run", help="Fallback Notion URL.")
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
            telegram_client = TelegramClient(settings.telegram_bot_token or "", settings.telegram_chat_id or "")

    store = MemoryStore(settings.memory_db)
    try:
        result = run_decision_review_pipeline(
            store=store,
            as_of=args.as_of,
            since=args.since,
            notion_url=args.notion_url,
            notion_client=notion_client,
            notion_database_id=settings.notion_daily_briefs_database_id,
            telegram_client=telegram_client,
            publish_notion=args.publish_notion,
            send_telegram=args.send_telegram,
        )
    except Exception as exc:
        send_pipeline_alert(
            store=store,
            pipeline="decision_review",
            error=exc,
            settings=settings,
            telegram_client=telegram_client,
        )
        print(f"Decision review run failed: {exc}")
        return 1
    finally:
        store.close()

    report = result.report
    print(report.title)
    print(report.executive_summary)
    print("Decision reviews:")
    if report.items:
        for item in report.items:
            print(f"- {item.original_action} / {item.signal_id}: {item.review_status} since {item.revisit_date}")
    else:
        print("- No decisions are due.")
    print("Top actions:")
    if report.top_actions:
        for action in report.top_actions:
            print(f"- {action}")
    else:
        print("- No review actions found in memory.")
    print(f"Notion: {result.notion.status} - {result.notion.detail}")
    print(f"Telegram: {result.telegram.status} - {result.telegram.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
