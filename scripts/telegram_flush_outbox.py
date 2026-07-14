from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from connectors.telegram import TelegramClient
from core.config import load_settings
from core.memory import MemoryStore
from core.notification_outbox import flush_pending_notifications


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send pending Intelligence Hub Telegram notifications from the local outbox.")
    parser.add_argument("--limit", type=int, help="Maximum pending notifications to send.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdout()
    args = parse_args()
    settings = load_settings(PROJECT_ROOT)
    if not settings.telegram_enabled:
        print("Telegram outbox flush failed: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not both set.")
        print("Aliases accepted: TELEGRAM_TOKEN or TG_BOT_TOKEN; TG_CHAT_ID.")
        return 1

    store = MemoryStore(settings.memory_db)
    try:
        pending_before = store.list_notification_outbox(status="pending")
        client = TelegramClient(settings.telegram_bot_token or "", settings.telegram_chat_id or "")
        sent = flush_pending_notifications(store=store, telegram_client=client, limit=args.limit)
        pending_after = store.list_notification_outbox(status="pending")
    finally:
        store.close()

    print(f"Telegram outbox pending before: {len(pending_before)}")
    print(f"Telegram outbox sent: {len(sent)}")
    print(f"Telegram outbox pending after: {len(pending_after)}")
    return 0 if not pending_after else 1


if __name__ == "__main__":
    raise SystemExit(main())
