from __future__ import annotations


def build_credential_updates(
    *,
    github_token: str | None = None,
    telegram_bot_token: str | None = None,
    telegram_chat_id: str | None = None,
    fast_model: str | None = None,
    pro_model: str | None = None,
) -> dict[str, str]:
    updates: dict[str, str] = {}
    if value := _clean(github_token):
        updates["GITHUB_TOKEN"] = value
    if value := _clean(telegram_bot_token):
        updates["TELEGRAM_BOT_TOKEN"] = value
    if value := _clean(telegram_chat_id):
        updates["TELEGRAM_CHAT_ID"] = value
    if value := _clean(fast_model):
        updates["HERMES_FAST_MODEL"] = value
    if value := _clean(pro_model):
        updates["HERMES_PRO_MODEL"] = value
    return updates


def mask_written_keys(updates: dict[str, str]) -> tuple[str, ...]:
    return tuple(key for key, value in updates.items() if value.strip())


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
