from __future__ import annotations

import pytest

from core.agent_runtime import AgentMetadata, FunctionAgent, AgentRegistry
from core.decision_engine import DecisionCandidate, DecisionEngine
from core.delivery import BriefDeliveryCoordinator, DeliveryStatus, MarkdownBriefRenderer
from core.intelligence_brief import IntelligenceBrief, IntelligenceSignal
from core.intelligence_engine import IntelligenceBuildInput, IntelligenceEngine
from core.knowledge_loader import load_knowledge_context
from core.memory import MemoryStore
from core.memory_engine import MemoryEngine
from core.synthesis_policy import SynthesisPolicy


def test_intelligence_brief_requires_structured_signal_fields() -> None:
    brief = IntelligenceBrief(
        brief_type="daily",
        domain="AI Intelligence",
        period_start="2026-07-10",
        period_end="2026-07-10",
        title="Daily",
        executive_summary="Summary",
        signals=(
            IntelligenceSignal(
                signal_id="github:repo",
                title="Repo",
                source_type="github",
                action="Read",
                confidence="medium",
                rationale="Rationale",
                why_now="It changed now.",
                what_changed="Stars increased.",
                connects_to="Agent workflows.",
                what_to_do="Read the release notes.",
            ),
        ),
    )

    brief.validate()
    assert brief.top_actions == ("Read: Repo",)


def test_decision_engine_ranks_once_and_falls_back_for_rationale() -> None:
    engine = DecisionEngine(top_ai_limit=5)
    candidates = (
        DecisionCandidate("b", "B", "paper", "Watch", "medium", strength=5),
        DecisionCandidate("a", "A", "github", "Prototype", "high", strength=1),
        DecisionCandidate("a2", "A", "github", "Read", "high", strength=100),
    )

    selected = engine.select_top(candidates, limit=2)
    rationale = engine.build_rationale(selected[0])

    assert [item.signal_id for item in selected] == ["a", "b"]
    assert engine.validate_rationale(rationale.fields) is True
    assert rationale.generated_by == "deterministic"


def test_synthesis_policy_downgrades_after_pro_limit() -> None:
    policy = SynthesisPolicy(mode="hybrid", pro_call_limit=1)

    assert policy.tier_for("daily_executive_summary") == "pro"
    assert policy.tier_for("top_decision_rationale") == "deterministic"
    assert policy.usage.pro_calls_used == 1
    assert policy.usage.fallback_count == 1


def test_intelligence_engine_uses_ai_for_top_decision_rationale_when_policy_allows() -> None:
    class Generator:
        def __init__(self) -> None:
            self.calls = []

        def generate(self, prompt: str, *, tier: str = "pro") -> str:
            self.calls.append((prompt, tier))
            return (
                '{"why_now":"AI why now","what_changed":"AI changed",'
                '"connects_to":"AI context","what_to_do":"AI action"}'
            )

    class Entity:
        canonical_name = "Signal A"
        tags = ("github", "ai-agent")

    class Decision:
        signal_id = "github:signal-a"
        action = "Prototype"
        confidence = "high"
        rationale = "Existing rationale"

    class Result:
        entity = Entity()
        decision = Decision()
        star_delta = 100
        momentum = "rising"

    generator = Generator()
    policy = SynthesisPolicy(mode="hybrid", pro_call_limit=1)
    brief = IntelligenceEngine(synthesis_policy=policy, generator=generator).build_brief(
        IntelligenceBuildInput(
            brief_type="daily",
            domain="AI Intelligence",
            period_start="2026-07-10",
            period_end="2026-07-10",
            title="Daily",
            fallback_summary="Summary",
            repository_results=(Result(),),
            knowledge_context="Use decision framework.",
            knowledge_used=("decision_framework",),
        )
    )

    assert generator.calls and generator.calls[0][1] == "pro"
    assert "Use decision framework." in generator.calls[0][0]
    assert brief.signals[0].why_now == "AI why now"
    assert brief.signals[0].evidence[-1] == "rationale_generated_by=ai"
    assert brief.synthesis_metadata.pro_calls_used == 1
    assert brief.synthesis_metadata.knowledge_used == ("decision_framework",)


def test_delivery_coordinator_uses_brief_contract(tmp_path) -> None:
    class Publisher:
        channel = "obsidian"

        def publish(self, brief, rendered):
            assert "# Daily" in rendered
            return DeliveryStatus("obsidian", "published", "ok")

    brief = IntelligenceBrief(
        brief_type="daily",
        domain="AI Intelligence",
        period_start="2026-07-10",
        period_end="2026-07-10",
        title="Daily",
        executive_summary="Summary",
    )
    coordinator = BriefDeliveryCoordinator(
        renderers={"markdown": MarkdownBriefRenderer()},
        publishers={"obsidian": Publisher()},
    )

    assert coordinator.deliver(brief, requested=("obsidian",)) == (DeliveryStatus("obsidian", "published", "ok"),)


def test_memory_engine_schema_stats_and_metadata(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        engine = MemoryEngine(store)
        brief = IntelligenceBrief(
            brief_type="daily",
            domain="AI Intelligence",
            period_start="2026-07-10",
            period_end="2026-07-10",
            title="Daily",
            executive_summary="Summary",
        )
        record = engine.record_brief(brief)
        stats = engine.stats()

        assert record.title == "Daily"
        assert stats.schema_version == "3"
        assert stats.table_rows["briefs"] == 1
    finally:
        store.close()


def test_knowledge_loader_allows_only_declared_files(tmp_path) -> None:
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "identity.md").write_text("# Identity\nHermes", encoding="utf-8")

    result = load_knowledge_context(knowledge, keys=("identity",), char_limit=20)

    assert result.used_keys == ("identity",)
    assert "Hermes" in result.render_context()
    with pytest.raises(ValueError):
        load_knowledge_context(knowledge, keys=("docs",))


def test_agent_registry_registers_ai_style_agents() -> None:
    registry = AgentRegistry()
    registry.register(
        FunctionAgent(
            AgentMetadata(
                agent_id="ai_intelligence",
                domain="AI Intelligence",
                ingestor_types=("github",),
                workflow="daily_intelligence",
                synthesis_policy="hybrid",
                publishers=("obsidian",),
            ),
            lambda **kwargs: kwargs["value"],
        )
    )

    assert registry.get("ai_intelligence").run(value=42) == 42
    assert registry.list_agents()[0].agent_id == "ai_intelligence"
