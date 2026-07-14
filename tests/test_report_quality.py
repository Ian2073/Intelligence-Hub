from __future__ import annotations

from core.report_quality import build_executive_judgment, unique_actions, validate_brief_quality


def test_unique_actions_compacts_rationale_and_deduplicates_entities() -> None:
    actions = (
        "Prototype: RAG-Anything connects to 3 radar entities. 下一步：檢查 HKUDS/RAG-Anything 是否能做最小驗證。",
        "Prototype: RAG-Anything connects to 3 radar entities. 下一步：重複項目。",
        "Read: NVIDIA Nemotron Achieves Benchmark-Leading Performance With LangChain Deep Agents Harness (impact 53). 下一步：判斷路線。",
    )

    result = unique_actions(actions, limit=7, max_chars=120)

    assert result == (
        "Prototype: RAG-Anything 連到 3 個 radar 實體",
        "Read: NVIDIA Nemotron Achieves Benchmark-Leading Performance With LangChain Deep Agents Harness",
    )


def test_build_executive_judgment_leads_with_decision_not_system_metrics() -> None:
    summary = build_executive_judgment(
        period_label="本週",
        top_actions=("Prototype: RAG-Anything connects to 3 radar entities.",),
        trends=(("Research-to-implementation", "Up", "3 paper observations"),),
    )

    assert "本週的判斷" in summary
    assert "Hermes used" not in summary
    assert not validate_brief_quality(
        executive_summary=summary,
        top_actions=("Prototype: RAG-Anything connects to 3 radar entities.",),
    )


def test_validate_brief_quality_flags_system_metric_summary_and_duplicates() -> None:
    issues = validate_brief_quality(
        executive_summary="This week Hermes used 2 daily briefs and 258 observations from memory.",
        top_actions=(
            "Read: NVIDIA signal",
            "Read: NVIDIA signal",
        ),
    )

    assert {issue.code for issue in issues} == {"duplicate_actions", "system_metric_summary", "weak_judgment"}
