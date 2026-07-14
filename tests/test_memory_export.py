from __future__ import annotations

import json

from core.memory import MemoryStore
from core.memory_export import export_memory


def test_export_memory_writes_jsonl_and_markdown_index(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        entity = store.upsert_entity(
            kind="technology",
            canonical_name="AI agents",
            observed_at="2026-07-01",
            tags=("agent",),
            summary="Agentic software systems.",
        )
        store.record_observation(
            entity_id=entity.id,
            observed_at="2026-07-02",
            source_type="domain:AI",
            source_url="local://signals/ai-agents",
            metric_name="impact_score",
            previous_value=70,
            current_value=85,
            raw_evidence="Signal evidence.",
            confidence="medium",
        )
        store.record_decision(
            signal_id="domain:AI:AI agents:2026-07-02",
            action="Watch",
            rationale="AI agents are gaining momentum.",
            expected_payoff="Track implementation implications.",
            risk="Hype cycle noise.",
            revisit_date="2026-07-09",
            confidence="medium",
        )
        store.record_brief(
            brief_type="daily",
            domain="AI Intelligence",
            period_start="2026-07-02",
            period_end="2026-07-02",
            title="Intelligence Hub Daily Brief - 2026-07-02",
            executive_summary="Daily summary.",
            top_actions=("Watch: AI agents are gaining momentum.",),
            notion_status="dry-run",
            notion_url="local://notion/daily",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
        )
        store.record_run(
            run_date="2026-07-02",
            stage="daily",
            title="Intelligence Hub Daily Brief - 2026-07-02",
            period_start="2026-07-02",
            period_end="2026-07-02",
            status="completed",
            notion_status="dry-run",
            notion_url="local://notion/daily",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
            created_at="2026-07-02T01:00:00+00:00",
        )
        store.enqueue_notification(
            title="Intelligence Hub Daily Brief - 2026-07-02",
            decisions=("Watch: AI agents are gaining momentum.",),
            top_action="Watch",
            notion_url="https://notion.so/hermes-daily",
            last_error="skipped: Missing Telegram client.",
            created_at="2026-07-02T01:05:00+00:00",
        )

        result = export_memory(store, output_dir=tmp_path / "export", as_of="2026-07-02")

        assert result.entity_count == 1
        assert result.observation_count == 1
        assert result.decision_count == 1
        assert result.brief_count == 1
        assert result.run_count == 1
        assert result.notification_outbox_count == 1
        entity_rows = result.entities_path.read_text(encoding="utf-8").splitlines()
        assert json.loads(entity_rows[0])["canonical_name"] == "AI agents"
        run_rows = result.runs_path.read_text(encoding="utf-8").splitlines()
        assert json.loads(run_rows[0])["stage"] == "daily"
        outbox_rows = result.notification_outbox_path.read_text(encoding="utf-8").splitlines()
        assert json.loads(outbox_rows[0])["top_action"] == "Watch"
        assert "| decisions.jsonl | 1 |" in result.index_path.read_text(encoding="utf-8")
        assert "| runs.jsonl | 1 |" in result.index_path.read_text(encoding="utf-8")
        assert "| notification_outbox.jsonl | 1 |" in result.index_path.read_text(encoding="utf-8")
    finally:
        store.close()
