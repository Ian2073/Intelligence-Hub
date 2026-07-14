from __future__ import annotations

from core.memory import MemoryStore
from workflows.executive_dashboard import build_executive_dashboard


def _seed_dashboard_memory(store: MemoryStore) -> None:
    for brief_type, title, end in (
        ("daily", "Hermes Daily Intelligence - 2026-07-08", "2026-07-08"),
        ("weekly", "Hermes Weekly Intelligence - 2026-07-01 to 2026-07-07", "2026-07-07"),
        ("monthly", "Hermes Monthly Intelligence - 2026-07-01 to 2026-07-31", "2026-07-31"),
    ):
        store.record_brief(
            brief_type=brief_type,
            domain="AI Intelligence",
            period_start=end,
            period_end=end,
            title=title,
            executive_summary=f"{brief_type} summary.",
            top_actions=("Prototype: Paper connects to implementation.", "Watch: OpenHands momentum active."),
            notion_status="dry-run",
            notion_url=f"local://notion/{brief_type}",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
        )


def test_build_executive_dashboard_uses_latest_briefs_and_deduplicates_actions(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        _seed_dashboard_memory(store)

        dashboard = build_executive_dashboard(
            store,
            as_of="2026-07-31",
            window_start="2026-07-01",
        )

        assert dashboard.title == "Hermes Executive Dashboard - 2026-07-31"
        assert len(dashboard.latest_items) == 3
        assert [item.label for item in dashboard.latest_items] == ["Daily", "Weekly", "Monthly"]
        assert dashboard.top_actions == (
            "Prototype: Paper connects to implementation.",
            "Watch: OpenHands momentum active.",
        )
        assert "最高優先行動" in dashboard.executive_summary
        assert "latest intelligence surfaces" not in dashboard.executive_summary
        assert "Operational health" in dashboard.executive_summary
        assert dashboard.operational_health[0].startswith("Pipeline runs:")
        assert "Memory tables:" in dashboard.operational_health[2]
    finally:
        store.close()


def test_build_executive_dashboard_prefers_published_brief_for_same_period(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        store.record_brief(
            brief_type="daily",
            domain="AI Intelligence",
            period_start="2026-07-08",
            period_end="2026-07-08",
            title="Hermes Daily Intelligence - dry run",
            executive_summary="Dry run summary.",
            top_actions=("Watch: dry run action.",),
            notion_status="dry-run",
            notion_url="local://notion/daily",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
        )
        store.record_brief(
            brief_type="daily",
            domain="AI Intelligence",
            period_start="2026-07-08",
            period_end="2026-07-08",
            title="Hermes Daily Intelligence - published",
            executive_summary="Published summary.",
            top_actions=("Prototype: published action.",),
            notion_status="published",
            notion_url="https://notion.so/published",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
        )

        dashboard = build_executive_dashboard(
            store,
            as_of="2026-07-08",
            window_start="2026-07-01",
        )

        assert dashboard.latest_items[0].title == "Hermes Daily Intelligence - published"
        assert dashboard.latest_items[0].status == "Notion=published, Telegram=dry-run"
        assert dashboard.top_actions == ("Prototype: published action.",)
    finally:
        store.close()
