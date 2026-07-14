from __future__ import annotations

from connectors.github import parse_repository_snapshot
from connectors.papers import parse_paper_snapshot
from core.github_radar import ingest_repository_snapshot
from core.memory import MemoryStore
from core.paper_radar import ingest_paper_snapshot
from workflows.weekly_intelligence import build_weekly_intelligence_report, build_weekly_report_from_memory


def _repo_payload(stars: int) -> dict:
    return {
        "owner": {"login": "All-Hands-AI"},
        "name": "OpenHands",
        "full_name": "All-Hands-AI/OpenHands",
        "html_url": "https://github.com/All-Hands-AI/OpenHands",
        "description": "AI software engineering agent.",
        "language": "Python",
        "stargazers_count": stars,
        "open_issues_count": 10,
        "topics": ["ai-agent"],
        "pushed_at": "2026-07-02T00:00:00Z",
        "updated_at": "2026-07-02T00:00:00Z",
        "default_branch": "main",
    }


def test_build_weekly_report_turns_daily_results_into_trends(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        ingest_repository_snapshot(
            store,
            parse_repository_snapshot(_repo_payload(24000), None, "2026-07-01"),
            revisit_date="2026-07-08",
        )
        repo_result = ingest_repository_snapshot(
            store,
            parse_repository_snapshot(
                _repo_payload(25500),
                {"tag_name": "v1.2.0", "html_url": "https://github.com/release", "published_at": "2026-07-02"},
                "2026-07-02",
            ),
            revisit_date="2026-07-09",
        )
        paper_result = ingest_paper_snapshot(
            store,
            parse_paper_snapshot(
                {
                    "title": "Agentic Retrieval for Code Editing",
                    "url": "https://arxiv.org/abs/2607.00001",
                    "published_at": "2026-07-01",
                    "authors": ["A. Researcher"],
                    "abstract": "A paper about agentic retrieval for code editing.",
                    "categories": ["cs.AI"],
                    "technologies": ["AI agents"],
                    "repositories": ["All-Hands-AI/OpenHands"],
                    "companies": [],
                },
                "2026-07-02",
            ),
            revisit_date="2026-07-09",
        )

        report = build_weekly_intelligence_report(
            period_start="2026-07-01",
            period_end="2026-07-07",
            repository_results=(repo_result,),
            paper_results=(paper_result,),
        )

        assert report.title == "Intelligence Hub Weekly Brief - 2026-07-01 to 2026-07-07"
        assert "Open-source AI engineering" in [trend.name for trend in report.trends]
        assert report.trends[0].direction == "Up"
        assert report.top_actions[0].startswith("Prototype:")
    finally:
        store.close()


def test_build_weekly_report_from_memory_uses_daily_briefs_and_observations(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
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
            current_value=25500,
            raw_evidence="GitHub snapshot.",
            confidence="high",
        )
        store.record_brief(
            brief_type="daily",
            domain="AI Intelligence",
            period_start="2026-07-02",
            period_end="2026-07-02",
            title="Intelligence Hub Daily Brief - 2026-07-02",
            executive_summary="Open-source AI engineering moved.",
            top_actions=("Prototype: OpenHands has strong momentum.",),
            notion_status="dry-run",
            notion_url="local://notion/dry-run",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
        )
        store.record_decision(
            signal_id="repo:All-Hands-AI/OpenHands",
            action="Prototype",
            rationale="Momentum crossed the weekly threshold.",
            expected_payoff="Validate agent workflow gains.",
            risk="Could duplicate existing tooling.",
            revisit_date="2026-07-07",
            confidence="high",
        )

        report = build_weekly_report_from_memory(
            store,
            period_start="2026-07-01",
            period_end="2026-07-07",
        )

        assert "本週" in report.executive_summary
        assert "最高優先行動" in report.executive_summary
        assert "daily briefs" not in report.executive_summary
        assert "1 個舊決策需要回看" in report.executive_summary
        assert report.trends[0].direction == "Up"
        assert report.top_actions == (
            "Prototype: OpenHands has strong momentum.",
            "Review later: Revisit Prototype decision for repo:All-Hands-AI/OpenHands (due 2026-07-07) - Momentum crossed the weekly threshold.",
        )
        assert report.decision_reviews[0].signal_id == "repo:All-Hands-AI/OpenHands"
    finally:
        store.close()
