from __future__ import annotations

from core.delivery import DeliveryStatus, telegram_blocked_by_notion


def test_telegram_blocked_by_notion_allows_published_pages() -> None:
    assert telegram_blocked_by_notion(DeliveryStatus("notion", "published", "https://notion.so/page")) is None


def test_telegram_blocked_by_notion_blocks_dry_run_links() -> None:
    status = telegram_blocked_by_notion(DeliveryStatus("notion", "dry-run", "local://notion/dry-run"))

    assert status == DeliveryStatus(
        channel="telegram",
        status="skipped",
        detail="Notion status is dry-run; notification not sent.",
    )
