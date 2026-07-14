from __future__ import annotations

import os
import subprocess
import sys

from core.credential_setup import build_credential_updates, mask_written_keys


def test_build_credential_updates_writes_standard_go_live_keys() -> None:
    updates = build_credential_updates(
        github_token="  ghp-token  ",
        telegram_bot_token="  tg-token  ",
        telegram_chat_id="  123456  ",
        fast_model="  cheap-fast  ",
        pro_model="  strong-pro  ",
    )

    assert updates == {
        "GITHUB_TOKEN": "ghp-token",
        "TELEGRAM_BOT_TOKEN": "tg-token",
        "TELEGRAM_CHAT_ID": "123456",
        "HERMES_FAST_MODEL": "cheap-fast",
        "HERMES_PRO_MODEL": "strong-pro",
    }


def test_build_credential_updates_skips_empty_values() -> None:
    updates = build_credential_updates(
        github_token="",
        telegram_bot_token=None,
        telegram_chat_id=" chat ",
    )

    assert updates == {"TELEGRAM_CHAT_ID": "chat"}


def test_mask_written_keys_returns_only_key_names() -> None:
    updates = {"GITHUB_TOKEN": "secret", "HERMES_FAST_MODEL": "cheap-fast"}

    assert mask_written_keys(updates) == ("GITHUB_TOKEN", "HERMES_FAST_MODEL")


def test_configure_credentials_from_env_writes_models_without_printing_values(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("HERMES_FAST_MODEL=old-fast\n", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        {
            "HERMES_SETUP_GITHUB_TOKEN": "ghx",
            "HERMES_SETUP_TELEGRAM_BOT_TOKEN": "tgx",
            "HERMES_SETUP_TELEGRAM_CHAT_ID": "chat-id",
            "HERMES_SETUP_FAST_MODEL": "cheap-fast",
            "HERMES_SETUP_PRO_MODEL": "strong-pro",
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/configure_credentials.py",
            "--from-env",
            "--env-file",
            str(env_file),
        ],
        cwd=".",
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    content = env_file.read_text(encoding="utf-8")
    assert "GITHUB_TOKEN=ghx" in content
    assert "TELEGRAM_BOT_TOKEN=tgx" in content
    assert "TELEGRAM_CHAT_ID=chat-id" in content
    assert "HERMES_FAST_MODEL=cheap-fast" in content
    assert "HERMES_PRO_MODEL=strong-pro" in content
    assert "ghx" not in result.stdout
    assert "tgx" not in result.stdout
    assert "cheap-fast" not in result.stdout
    assert "strong-pro" not in result.stdout
