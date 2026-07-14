from __future__ import annotations

from core.env_file import update_env_values


def test_update_env_values_preserves_existing_lines_and_updates_keys(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "NOTION_TOKEN=secret",
                "NOTION_DAILY_BRIEFS_DATABASE_ID=old-briefs",
                "",
                "# Telegram",
                "TELEGRAM_CHAT_ID=chat",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    update_env_values(
        env_path,
        {
            "NOTION_DAILY_BRIEFS_DATABASE_ID": "new-briefs",
            "NOTION_PAPERS_DATABASE_ID": "papers-id",
        },
    )

    assert env_path.read_text(encoding="utf-8").splitlines() == [
        "NOTION_TOKEN=secret",
        "NOTION_DAILY_BRIEFS_DATABASE_ID=new-briefs",
        "",
        "# Telegram",
        "TELEGRAM_CHAT_ID=chat",
        "",
        "NOTION_PAPERS_DATABASE_ID=papers-id",
    ]
