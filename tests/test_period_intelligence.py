from __future__ import annotations

from core.memory import MemoryStore
from workflows.period_intelligence import build_monthly_report_from_memory


def _seed_month_memory(store: MemoryStore) -> None:
    entity = store.upsert_entity(
        kind="repository",
        canonical_name="All-Hands-AI/OpenHands",
        observed_at="2026-07-02",
    )
    store.record_observation(
        entity_id=entity.id,
        observed_at="2026-07-02",
        source_type="github",
        source_url="https://github.com/All-Hands-AI/OpenHands",
        metric_name="stars",
        previous_value=24000,
        current_value=25800,
        raw_evidence="GitHub snapshot.",
        confidence="high",
    )
    for day in ("2026-07-02", "2026-07-09"):
        store.record_brief(
            brief_type="weekly",
            domain="AI Intelligence",
            period_start=day,
            period_end=day,
            title=f"Intelligence Hub Weekly Brief - {day}",
            executive_summary="Research-to-implementation moved.",
            top_actions=("Prototype: OpenHands has strong momentum.", "Watch: MCP remains active."),
            notion_status="dry-run",
            notion_url="local://notion/weekly",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
        )


def test_build_monthly_report_from_memory_uses_weekly_and_daily_memory(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        _seed_month_memory(store)

        report = build_monthly_report_from_memory(
            store,
            period_start="2026-07-01",
            period_end="2026-07-31",
        )

        assert report.brief_type == "monthly"
        assert report.title == "Intelligence Hub Monthly Brief - 2026-07-01 to 2026-07-31"
        assert "本月" in report.executive_summary
        assert "最高優先行動" in report.executive_summary
        assert "weekly briefs" not in report.executive_summary
        assert report.trends[0].direction == "Up"
        assert report.top_actions == (
            "Prototype: OpenHands has strong momentum.",
            "Watch: MCP remains active.",
        )
    finally:
        store.close()
