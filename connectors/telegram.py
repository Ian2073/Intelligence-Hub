from __future__ import annotations

from dataclasses import dataclass

import httpx

from connectors.retry import retry_on_transient


class TelegramError(RuntimeError):
    pass


@dataclass(frozen=True)
class TelegramNotification:
    title: str
    decisions: tuple[str, ...]
    top_action: str
    notion_url: str
    executive_summary: str = ""


@dataclass(frozen=True)
class TelegramResult:
    message_id: int


@dataclass(frozen=True)
class TelegramBotInfo:
    id: int
    username: str


class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str, timeout: float = 30.0) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout

    def send_notification(self, notification: TelegramNotification) -> TelegramResult:
        payload = build_telegram_payload(self.chat_id, notification)
        try:
            response = retry_on_transient(
                lambda: httpx.post(
                    f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                    json=payload,
                    timeout=self.timeout,
                ),
                operation_name="Telegram API",
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise TelegramError(
                f"Telegram returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except Exception as exc:
            raise TelegramError(f"Telegram request failed: {exc}") from exc

        data = response.json()
        result = data.get("result") if isinstance(data, dict) else None
        if not isinstance(result, dict) or not isinstance(result.get("message_id"), int):
            raise TelegramError("Telegram did not return a message id.")
        return TelegramResult(message_id=result["message_id"])

    def get_me(self) -> TelegramBotInfo:
        try:
            response = retry_on_transient(
                lambda: httpx.get(
                    f"https://api.telegram.org/bot{self.bot_token}/getMe",
                    timeout=self.timeout,
                ),
                operation_name="Telegram API",
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise TelegramError(
                f"Telegram returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except Exception as exc:
            raise TelegramError(f"Telegram request failed: {exc}") from exc

        data = response.json()
        result = data.get("result") if isinstance(data, dict) else None
        if not isinstance(result, dict) or not isinstance(result.get("id"), int):
            raise TelegramError("Telegram did not return bot identity.")
        return TelegramBotInfo(
            id=result["id"],
            username=str(result.get("username") or "").strip(),
        )


def build_telegram_payload(chat_id: str, notification: TelegramNotification) -> dict:
    decisions = notification.decisions[:3]
    lines = [f"📊 <b>{_escape_html(notification.title.strip())}</b>", ""]
    if notification.executive_summary.strip():
        lines.append("💡 <b>核心情報精華</b>")
        lines.append(_escape_html(_telegram_summary(notification.executive_summary)))
        lines.append("")
    if decisions:
        lines.append("🎯 <b>最優決策與行動</b>")
        for index, decision in enumerate(decisions, start=1):
            lines.append(f"{_decision_emoji(decision)} {index}. {_escape_html(decision)}")
    else:
        lines.append("✅ No high-priority decisions.")
    lines.append("")
    lines.append(f"🎯 Top action: <b>{_escape_html(notification.top_action)}</b>")
    lines.append(f"📝 Notion: {notification.notion_url}")
    return {
        "chat_id": chat_id,
        "text": "\n".join(lines),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }


def _decision_emoji(decision: str) -> str:
    text = decision.casefold()
    if "prototype" in text:
        return "🔥"
    if "implement" in text:
        return "🚀"
    if "read" in text:
        return "📖"
    if "watch" in text:
        return "👀"
    return "📌"


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _telegram_summary(text: str, max_chars: int = 450) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip(" ,，;；") + "…"
