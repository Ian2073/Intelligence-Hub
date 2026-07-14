from __future__ import annotations

from core.memory import MemoryStore
from workflows.decision_review import build_decision_review_report


def test_build_decision_review_report_returns_due_and_overdue_decisions(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        watch = store.record_decision(
            signal_id="repo:All-Hands-AI/OpenHands",
            action="Watch",
            rationale="Momentum was not yet strong enough to prototype.",
            expected_payoff="Avoid shallow prototype work.",
            risk="May miss acceleration.",
            revisit_date="2026-07-07",
            confidence="medium",
        )
        prototype = store.record_decision(
            signal_id="paper:agentic-retrieval",
            action="Prototype",
            rationale="Paper connects directly to code editing agents.",
            expected_payoff="Could improve internal agent workflows.",
            risk="Prototype may not transfer to production.",
            revisit_date="2026-07-06",
            confidence="high",
        )
        store.record_decision(
            signal_id="company:Example",
            action="Read",
            rationale="Future event.",
            expected_payoff="None yet.",
            risk="Low.",
            revisit_date="2026-07-10",
            confidence="low",
        )

        report = build_decision_review_report(store, as_of="2026-07-07", since="2026-07-01")

        assert report.title == "Hermes Decision Review - 2026-07-07"
        assert "2 個決策需要處理" in report.executive_summary
        assert "最高優先" in report.executive_summary
        assert [item.decision_id for item in report.items] == [prototype.id, watch.id]
        assert report.items[0].review_status == "overdue"
        assert report.items[1].review_status == "due"
        assert report.top_actions[0].startswith("Review later: Revisit Prototype decision")
        assert len(report.top_actions) <= 7
    finally:
        store.close()
