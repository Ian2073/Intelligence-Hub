from __future__ import annotations

from connectors.telegram import TelegramNotification, build_telegram_payload


def test_build_telegram_payload_limits_daily_notification_to_three_decisions() -> None:
    payload = build_telegram_payload(
        "12345",
        TelegramNotification(
            title="Intelligence Hub Daily Brief",
            decisions=(
                "[Prototype] OpenHands momentum surged",
                "[Read] vLLM release affects inference",
                "[Watch] MCP adoption continues",
                "[Ignore] Low-signal marketing post",
            ),
            top_action="Prototype",
            notion_url="https://notion.so/hermes-daily",
        ),
    )

    assert payload["chat_id"] == "12345"
    assert "1. [Prototype] OpenHands momentum surged" in payload["text"]
    assert "3. [Watch] MCP adoption continues" in payload["text"]
    assert "Low-signal marketing post" not in payload["text"]
    assert "Notion: https://notion.so/hermes-daily" in payload["text"]
    assert payload["disable_web_page_preview"] is True


def test_build_telegram_payload_includes_compact_executive_summary() -> None:
    payload = build_telegram_payload(
        "12345",
        TelegramNotification(
            title="Intelligence Hub Weekly Brief",
            decisions=("Prototype: RAG-Anything",),
            top_action="Prototype",
            notion_url="local://notion/weekly",
            executive_summary="本週的判斷是：" + "高價值訊號需要處理。" * 80,
        ),
    )

    text = payload["text"]
    assert "核心情報精華" in text
    assert "最優決策與行動" in text
    assert len(text) < 900
    assert "…" in text
