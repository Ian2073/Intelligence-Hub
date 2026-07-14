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
from core.radar_pipeline import run_radar_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Hermes Radar Snapshot from memory.")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="Snapshot date in YYYY-MM-DD format.")
    parser.add_argument("--since", help="Optional lower bound for observations and decisions.")
    parser.add_argument("--publish-notion", action="store_true", help="Publish Radar Snapshot to Notion.")
    parser.add_argument("--send-telegram", action="store_true", help="Send Telegram notification.")
    parser.add_argument("--notion-url", default="local://notion/radar-dry-run", help="Fallback Notion URL.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdout()
    args = parse_args()
    settings = load_settings(PROJECT_ROOT)
    since = args.since or (date.fromisoformat(args.as_of) - timedelta(days=30)).isoformat()
    notion_client = None
    if args.publish_notion:
        if not settings.notion_enabled:
            print("Notion publishing skipped: NOTION_TOKEN and NOTION_PARENT_PAGE_ID are required.")
        else:
            notion_client = NotionClient(settings.notion_token or "", settings.notion_parent_page_id or "")
    telegram_client = None
    if args.send_telegram:
        if not settings.telegram_enabled:
            print("Telegram send skipped: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not both set.")
        else:
            telegram_client = TelegramClient(settings.telegram_bot_token or "", settings.telegram_chat_id or "")

    store = MemoryStore(settings.memory_db)
    try:
        result = run_radar_pipeline(
            store=store,
            as_of=args.as_of,
            since=since,
            notion_url=args.notion_url,
            notion_client=notion_client,
            notion_radar_database_id=settings.notion_radar_snapshots_database_id,
            notion_radar_entities_database_id=settings.notion_radar_entities_database_id,
            notion_decisions_database_id=settings.notion_decisions_database_id,
            telegram_client=telegram_client,
            publish_notion=args.publish_notion,
            send_telegram=args.send_telegram,
        )
    except Exception as exc:
        send_pipeline_alert(
            store=store,
            pipeline="radar",
            error=exc,
            settings=settings,
            telegram_client=telegram_client,
        )
        print(f"Radar snapshot run failed: {exc}")
        return 1
    finally:
        store.close()

    print(result.snapshot.title)
    print(result.snapshot.executive_summary)
    print(f"Radar entries: {len(result.snapshot.entries)}")
    for entry in result.snapshot.entries[:10]:
        print(f"- [{entry.kind}] {entry.name}: {entry.observation_count} observations, {entry.relationship_count} links")
    print(f"Notion: {result.notion.status} - {result.notion.detail}")
    print(f"Telegram: {result.telegram.status} - {result.telegram.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
