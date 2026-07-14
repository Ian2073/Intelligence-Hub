from __future__ import annotations

from connectors.domain import parse_domain_signal_snapshot
from core.domain_radar import _impact_score, ingest_domain_signal_snapshot
from core.memory import MemoryStore


def test_ingest_domain_signal_creates_decision_and_relationships(tmp_path) -> None:
    snapshot = parse_domain_signal_snapshot(
        {
            "domain": "Cybersecurity Intelligence",
            "title": "Agentic systems need security evaluation",
            "entity_name": "Agentic security evaluation",
            "entity_kind": "technology",
            "source_url": "local://signals/cybersecurity/agentic-security-evaluation",
            "published_at": "2026-07-01",
            "summary": "Agents need tool abuse and prompt injection evaluation.",
            "evidence": "Tool permissions and retrieval poisoning create new attack paths.",
            "impact_score": 88,
            "confidence": "high",
            "tags": ["cybersecurity", "evals"],
            "technologies": ["AI agents", "Security evals"],
            "companies": ["OpenAI"],
            "repositories": ["All-Hands-AI/OpenHands"],
            "recommended_action": "Prototype",
        },
        "2026-07-02",
    )
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        result = ingest_domain_signal_snapshot(store, snapshot, revisit_date="2026-07-09")

        assert result.entity.canonical_name == "Agentic security evaluation"
        assert result.decision.action == "Prototype"
        assert result.priority_score == 88
        assert len(result.relationships) == 4
        assert result.brief_line.startswith("Prototype: [Cybersecurity Intelligence]")
        assert "Why now:" in result.decision.rationale
        assert "What changed:" in result.decision.rationale
        assert "Connects to:" in result.decision.rationale
        assert "What to do:" in result.decision.rationale
        assert "Confidence:" in result.decision.rationale
    finally:
        store.close()


def test_domain_signal_tracks_impact_momentum(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        old = parse_domain_signal_snapshot(
            {
                "domain": "Startup Intelligence",
                "title": "AI developer tools consolidate",
                "entity_name": "AI developer tool consolidation",
                "entity_kind": "trend",
                "source_url": "local://signals/startup/ai-developer-tool-consolidation",
                "published_at": "2026-07-01",
                "summary": "Workflow ownership matters.",
                "evidence": "Narrow completion tools lose leverage.",
                "impact_score": 60,
                "confidence": "medium",
            },
            "2026-07-01",
        )
        ingest_domain_signal_snapshot(store, old, revisit_date="2026-07-08")
        current = parse_domain_signal_snapshot(
            {
                "domain": "Startup Intelligence",
                "title": "AI developer tools consolidate",
                "entity_name": "AI developer tool consolidation",
                "entity_kind": "trend",
                "source_url": "local://signals/startup/ai-developer-tool-consolidation",
                "published_at": "2026-07-02",
                "summary": "Workflow ownership matters.",
                "evidence": "More evidence confirms the trend.",
                "impact_score": 80,
                "confidence": "medium",
                "technologies": ["AI agents"],
            },
            "2026-07-02",
        )

        result = ingest_domain_signal_snapshot(store, current, revisit_date="2026-07-09")

        assert result.priority_score == 100
        assert "(impact 80, +20 since last observation)" in result.brief_line
    finally:
        store.close()


def test_domain_impact_score_weights_velocity_cross_signal_relevance_and_novelty() -> None:
    snapshot = parse_domain_signal_snapshot(
        {
            "domain": "AI Intelligence",
            "title": "Agent workflow acceleration",
            "entity_name": "Agent workflow acceleration",
            "entity_kind": "trend",
            "source_url": "local://signals/agents",
            "published_at": "2026-07-02",
            "summary": "Agent workflow tooling is moving into production.",
            "evidence": "Multiple platforms shipped tool use updates.",
            "impact_score": 80,
            "confidence": "medium",
        },
        "2026-07-02",
    )

    assert _impact_score(snapshot, score_delta=20, relationship_count=2, history=[]) == 80
    assert _impact_score(snapshot, score_delta=0, relationship_count=0, history=[]) == 48
