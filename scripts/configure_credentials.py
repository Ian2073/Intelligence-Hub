from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.credential_setup import build_credential_updates, mask_written_keys
from core.env_file import update_env_values


ENV_GITHUB_TOKEN = "HERMES_SETUP_GITHUB_TOKEN"
ENV_TELEGRAM_BOT_TOKEN = "HERMES_SETUP_TELEGRAM_BOT_TOKEN"
ENV_TELEGRAM_CHAT_ID = "HERMES_SETUP_TELEGRAM_CHAT_ID"
ENV_FAST_MODEL = "HERMES_SETUP_FAST_MODEL"
ENV_PRO_MODEL = "HERMES_SETUP_PRO_MODEL"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Configure Intelligence Hub credentials in .env without printing secrets.")
    parser.add_argument("--from-env", action="store_true", help="Read credentials from HERMES_SETUP_* environment variables.")
    parser.add_argument("--env-file", default=".env", help="Environment file to update. Defaults to .env.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdout()
    args = parse_args()
    env_path = Path(args.env_file)
    if not env_path.is_absolute():
        env_path = PROJECT_ROOT / env_path

    if args.from_env:
        updates = build_credential_updates(
            github_token=os.getenv(ENV_GITHUB_TOKEN),
            telegram_bot_token=os.getenv(ENV_TELEGRAM_BOT_TOKEN),
            telegram_chat_id=os.getenv(ENV_TELEGRAM_CHAT_ID),
            fast_model=os.getenv(ENV_FAST_MODEL),
            pro_model=os.getenv(ENV_PRO_MODEL),
        )
    else:
        updates = _prompt_updates()

    if not updates:
        print("No credential values provided; .env was not changed.")
        return 1

    update_env_values(env_path, updates)
    print(f"Intelligence Hub credentials updated in {env_path}.")
    for key in mask_written_keys(updates):
        print(f"- {key}=<configured>")
    print("Next checks:")
    print(".\\hub_env\\Scripts\\python.exe scripts\\github_check.py")
    print(".\\hub_env\\Scripts\\python.exe scripts\\telegram_check.py")
    print(".\\hub_env\\Scripts\\python.exe scripts\\go_live_check.py --live")
    print(".\\hub_env\\Scripts\\python.exe scripts\\readiness_audit.py --live")
    return 0


def _prompt_updates() -> dict[str, str]:
    print("Press Enter to skip any value you do not want to update.")
    github_token = getpass.getpass("GITHUB_TOKEN: ")
    telegram_bot_token = getpass.getpass("TELEGRAM_BOT_TOKEN: ")
    telegram_chat_id = input("TELEGRAM_CHAT_ID: ").strip()
    fast_model = input("HERMES_FAST_MODEL: ").strip()
    pro_model = input("HERMES_PRO_MODEL: ").strip()
    return build_credential_updates(
        github_token=github_token,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        fast_model=fast_model,
        pro_model=pro_model,
    )


if __name__ == "__main__":
    raise SystemExit(main())
