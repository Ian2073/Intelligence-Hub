from __future__ import annotations

from connectors.domain import parse_domain_signal_snapshot
from connectors.github import parse_repository_snapshot
from connectors.papers import parse_paper_snapshot
from core.memory import MemoryStore
from workflows.daily_intelligence import run_daily_github_intelligence, run_daily_intelligence


def _repo_payload(full_name: str, stars: int) -> dict:
    owner, name = full_name.split("/", 1)
    return {
        "owner": {"login": owner},
        "name": name,
        "full_name": full_name,
        "html_url": f"https://github.com/{full_name}",
        "description": f"{name} repository.",
        "language": "Python",
        "stargazers_count": stars,
        "open_issues_count": 10,
        "topics": ["ai-agent"],
        "pushed_at": "2026-07-02T00:00:00Z",
        "updated_at": "2026-07-02T00:00:00Z",
        "default_branch": "main",
    }


def _paper_payload(title: str, *, repo: str = "example/project") -> dict:
    return {
        "title": title,
        "url": f"https://arxiv.org/abs/{abs(hash(title)) % 100000}",
        "published_at": "2026-07-02",
        "authors": ["A. Researcher"],
        "abstract": f"{title} introduces a new framework for agentic workflows with benchmark evidence.",
        "categories": ["cs.AI"],
        "technologies": ["AI agents"],
        "repositories": [repo],
        "companies": [],
    }


def _domain_payload(title: str, entity_name: str, impact_score: int = 72) -> dict:
    return {
        "domain": "AI Intelligence",
        "title": title,
        "entity_name": entity_name,
        "entity_kind": "trend",
        "source_url": f"https://example.com/{title.replace(' ', '-').casefold()}",
        "published_at": "2026-07-02",
        "summary": f"{entity_name} is moving from research into production decisions.",
        "evidence": f"RSS item: {title}",
        "impact_score": impact_score,
        "confidence": "medium",
        "technologies": ["AI agents"],
        "companies": [],
        "repositories": [],
    }


def test_run_daily_github_intelligence_builds_ranked_notification(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        old = parse_repository_snapshot(_repo_payload("All-Hands-AI/OpenHands", 24000), None, "2026-07-01")
        run_daily_github_intelligence(
            store,
            [old],
            run_date="2026-07-01",
            revisit_date="2026-07-08",
            notion_url="local://notion/dev",
        )

        active = parse_repository_snapshot(
            _repo_payload("All-Hands-AI/OpenHands", 25500),
            {"tag_name": "v1.2.0", "html_url": "https://github.com/release", "published_at": "2026-07-02"},
            "2026-07-02",
        )
        flat = parse_repository_snapshot(_repo_payload("example/QuietRepo", 10), None, "2026-07-02")
        result = run_daily_github_intelligence(
            store,
            [flat, active],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="https://notion.so/hermes-daily",
        )

        assert result.notification.top_action == "Prototype"
        assert result.notification.decisions[0].startswith("Prototype: All-Hands-AI/OpenHands")
        assert result.notification.notion_url == "https://notion.so/hermes-daily"
    finally:
        store.close()


def test_run_daily_intelligence_deduplicates_repeated_papers_in_top_decisions(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        duplicate = _paper_payload("Zep: A Temporal Knowledge Graph Architecture for Agent Memory", repo="getzep/graphiti")
        result = run_daily_intelligence(
            store,
            [],
            paper_snapshots=[
                parse_paper_snapshot(duplicate, "2026-07-02"),
                parse_paper_snapshot(duplicate, "2026-07-02"),
                parse_paper_snapshot(_paper_payload("RAG-Anything: All-in-One RAG Framework", repo="HKUDS/RAG-Anything"), "2026-07-02"),
            ],
            domain_snapshots=[],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dev",
        )

        zep_decisions = [line for line in result.notification.decisions if "Zep:" in line]
        assert len(zep_decisions) == 1
        assert len(result.notification.decisions) == 2
    finally:
        store.close()


def test_run_daily_intelligence_keeps_best_domain_signal_per_entity(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        result = run_daily_intelligence(
            store,
            [],
            paper_snapshots=[],
            domain_snapshots=[
                parse_domain_signal_snapshot(_domain_payload("Early agent security note", "Agentic security evaluation", 52), "2026-07-02"),
                parse_domain_signal_snapshot(_domain_payload("Five Eyes agent security warning", "Agentic security evaluation", 82), "2026-07-02"),
            ],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dev",
        )

        assert len(result.notification.decisions) == 1
        assert "Five Eyes agent security warning" in result.notification.decisions[0]
    finally:
        store.close()


def test_run_daily_intelligence_prioritizes_analysis_over_baseline_repos(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        repos = [
            parse_repository_snapshot(
                _repo_payload(f"example/baseline-{index}", 100000 - index),
                {"tag_name": f"v1.{index}.0", "html_url": "https://github.com/release", "published_at": "2026-07-01"},
                "2026-07-02",
            )
            for index in range(8)
        ]
        result = run_daily_intelligence(
            store,
            repos,
            paper_snapshots=[
                parse_paper_snapshot(_paper_payload("Agent READMEs: An Empirical Study of Context Files for Agentic Coding"), "2026-07-02")
            ],
            domain_snapshots=[
                parse_domain_signal_snapshot(_domain_payload("NVIDIA agent inference update", "Inference platform moat", 74), "2026-07-02")
            ],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dev",
        )

        combined = "\n".join(result.notification.decisions)
        assert "Agent READMEs" in combined
        assert "NVIDIA agent inference update" in combined
        assert sum(1 for line in result.notification.decisions if "baseline-" in line) <= 3
    finally:
        store.close()
