from __future__ import annotations

import logging
from dataclasses import dataclass

from core.cross_signal_analysis import analyze_cross_signals
from core.decision_engine import DecisionCandidate, DecisionEngine, RationaleGenerator
from core.intelligence_brief import CrossSignal, IntelligenceBrief, IntelligenceSignal, SynthesisMetadata
from core.synthesis_policy import SynthesisPolicy


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IntelligenceBuildInput:
    brief_type: str
    domain: str
    period_start: str
    period_end: str
    title: str
    fallback_summary: str
    repository_results: tuple = ()
    paper_results: tuple = ()
    domain_results: tuple = ()
    memory_links: tuple[str, ...] = ()
    knowledge_context: str = ""
    knowledge_used: tuple[str, ...] = ()


class IntelligenceEngine:
    def __init__(
        self,
        *,
        decision_engine: DecisionEngine | None = None,
        synthesis_policy: SynthesisPolicy | None = None,
        generator: RationaleGenerator | None = None,
    ) -> None:
        self.decision_engine = decision_engine or DecisionEngine()
        self.synthesis_policy = synthesis_policy or SynthesisPolicy.from_env()
        self.generator = generator

    def build_brief(self, data: IntelligenceBuildInput) -> IntelligenceBrief:
        candidates = _candidates_from_results((*data.repository_results, *data.paper_results, *data.domain_results))
        selected = self.decision_engine.select_top(candidates, limit=7)
        signals = tuple(self._signal_from_candidate(candidate, index=index, data=data) for index, candidate in enumerate(selected))
        cross_signals = tuple(
            CrossSignal(
                title=item.title,
                subject=item.subject,
                sources=item.sources,
                rationale=item.rationale,
                confidence=item.confidence,
            )
            for item in analyze_cross_signals(data.repository_results, data.paper_results, data.domain_results)
        )
        brief = IntelligenceBrief(
            brief_type=data.brief_type,
            domain=data.domain,
            period_start=data.period_start,
            period_end=data.period_end,
            title=data.title,
            executive_summary=data.fallback_summary,
            signals=signals,
            cross_signals=cross_signals,
            memory_links=data.memory_links,
            synthesis_metadata=SynthesisMetadata(
                mode=self.synthesis_policy.mode,
                tier="deterministic",
                fallback_used=self.synthesis_policy.usage.fallback_count > 0,
                pro_calls_used=self.synthesis_policy.usage.pro_calls_used,
                pro_call_limit=self.synthesis_policy.pro_call_limit,
                knowledge_used=data.knowledge_used,
            ),
        )
        brief.validate()
        return brief

    def _signal_from_candidate(self, candidate: DecisionCandidate, *, index: int, data: IntelligenceBuildInput) -> IntelligenceSignal:
        tier = (
            self.synthesis_policy.tier_for("top_decision_rationale")
            if self.generator is not None and index < self.decision_engine.top_ai_limit
            else "deterministic"
        )
        rationale = self.decision_engine.build_rationale(
            candidate,
            generator=self.generator,
            use_ai=tier == "pro" and self.generator is not None,
            knowledge_context=data.knowledge_context,
        )
        if rationale.fallback_used:
            self.synthesis_policy.record_fallback()
        return IntelligenceSignal(
            signal_id=candidate.signal_id,
            title=candidate.title,
            source_type=candidate.source_type,
            action=candidate.action,
            confidence=candidate.confidence,
            rationale=rationale.text,
            why_now=rationale.fields.why_now,
            what_changed=rationale.fields.what_changed,
            connects_to=rationale.fields.connects_to,
            what_to_do=rationale.fields.what_to_do,
            evidence=candidate.evidence
            + ((f"synthesis_tier={tier}",) if tier != "deterministic" else ())
            + (f"rationale_generated_by={rationale.generated_by}",),
        )


def _candidates_from_results(results: tuple) -> tuple[DecisionCandidate, ...]:
    candidates = []
    for result in results:
        decision = result.decision
        title = getattr(result.entity, "canonical_name", str(decision.signal_id))
        source_type = str(decision.signal_id).split(":", 1)[0] or "unknown"
        evidence = tuple(_evidence_for_result(result))
        candidates.append(
            DecisionCandidate(
                signal_id=decision.signal_id,
                title=title,
                source_type=source_type,
                action=decision.action,
                confidence=decision.confidence,
                evidence=evidence,
                strength=_strength(result),
                rationale=decision.rationale,
            )
        )
    return tuple(candidates)


def _evidence_for_result(result) -> tuple[str, ...]:
    evidence = [getattr(result.decision, "rationale", "")]
    if hasattr(result, "star_delta"):
        evidence.append(f"star_delta={getattr(result, 'star_delta')}")
    if hasattr(result, "priority_score"):
        evidence.append(f"priority_score={getattr(result, 'priority_score')}")
    if hasattr(result, "relationships"):
        evidence.append(f"relationships={len(getattr(result, 'relationships', ())) }")
    return tuple(item for item in evidence if item)


def _strength(result) -> int:
    if hasattr(result, "priority_score"):
        return int(getattr(result, "priority_score"))
    if hasattr(result, "relationships"):
        return len(getattr(result, "relationships", ())) * 20
    return max(int(getattr(result, "star_delta", 0)), 0)
