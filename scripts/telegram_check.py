from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from connectors.telegram import TelegramClient, TelegramNotification
from core.config import load_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Hermes Telegram notification setup.")
    parser.add_argument("--send-test", action="store_true", help="Send a real Telegram test notification.")
    parser.add_argument(
        "--notion-url",
        default="https://notion.so/hermes-telegram-check",
        help="Notion URL to include in the optional test message.",
    )
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdout()
    args = parse_args()
    settings = load_settings(PROJECT_ROOT)
    missing = []
    if not settings.telegram_bot_token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not settings.telegram_chat_id:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        print(f"Telegram check failed: missing {', '.join(missing)}.")
        print("Aliases accepted: TELEGRAM_TOKEN or TG_BOT_TOKEN; TG_CHAT_ID.")
        return 1

    client = TelegramClient(
        bot_token=settings.telegram_bot_token or "",
        chat_id=settings.telegram_chat_id or "",
    )
    try:
        bot = client.get_me()
    except Exception as exc:
        print(f"Telegram bot identity check failed: {exc}")
        return 1

    username = f"@{bot.username}" if bot.username else str(bot.id)
    print(f"Telegram bot identity ok: {username}.")

    if not args.send_test:
        print("No test message sent. Pass --send-test to send a real notification.")
        return 0

    try:
        result = client.send_notification(
            TelegramNotification(
                title="Hermes Telegram Check",
                decisions=("Watch: Telegram delivery is configured.",),
                top_action="Watch",
                notion_url=args.notion_url,
            )
        )
    except Exception as exc:
        print(f"Telegram test message failed: {exc}")
        return 1
    print(f"Telegram test message sent: message_id={result.message_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
