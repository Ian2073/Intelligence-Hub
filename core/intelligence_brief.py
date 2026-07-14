from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from core.memory import BriefRecord, Decision


BriefType = Literal["daily", "weekly", "monthly", "dashboard", "radar", "decision_review", "demo"]


@dataclass(frozen=True)
class RationaleFields:
    why_now: str
    what_changed: str
    connects_to: str
    what_to_do: str

    def validate(self) -> None:
        for name, value in (
            ("why_now", self.why_now),
            ("what_changed", self.what_changed),
            ("connects_to", self.connects_to),
            ("what_to_do", self.what_to_do),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty.")


@dataclass(frozen=True)
class IntelligenceSignal:
    signal_id: str
    title: str
    source_type: str
    action: str
    confidence: str
    rationale: str
    why_now: str
    what_changed: str
    connects_to: str
    what_to_do: str
    evidence: tuple[str, ...] = ()

    @property
    def rationale_fields(self) -> RationaleFields:
        return RationaleFields(
            why_now=self.why_now,
            what_changed=self.what_changed,
            connects_to=self.connects_to,
            what_to_do=self.what_to_do,
        )

    def validate(self) -> None:
        for name, value in (
            ("signal_id", self.signal_id),
            ("title", self.title),
            ("source_type", self.source_type),
            ("action", self.action),
            ("confidence", self.confidence),
            ("rationale", self.rationale),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty.")
        self.rationale_fields.validate()


@dataclass(frozen=True)
class CrossSignal:
    title: str
    subject: str
    sources: tuple[str, ...]
    rationale: str
    confidence: str

    def validate(self) -> None:
        if not self.title.strip():
            raise ValueError("cross signal title must not be empty.")
        if not self.subject.strip():
            raise ValueError("cross signal subject must not be empty.")
        if not self.sources:
            raise ValueError("cross signal sources must not be empty.")


@dataclass(frozen=True)
class SynthesisMetadata:
    mode: str = "hybrid"
    tier: str = "deterministic"
    fallback_used: bool = False
    fallback_reason: str = ""
    pro_calls_used: int = 0
    pro_call_limit: int = 0
    knowledge_used: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "tier": self.tier,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "pro_calls_used": self.pro_calls_used,
            "pro_call_limit": self.pro_call_limit,
            "knowledge_used": list(self.knowledge_used),
        }


@dataclass(frozen=True)
class DeliveryHints:
    primary_publisher: str = "obsidian"
    requested_publishers: tuple[str, ...] = ("obsidian",)
    telegram_requires_primary_success: bool = True


@dataclass(frozen=True)
class IntelligenceBrief:
    brief_type: BriefType | str
    domain: str
    period_start: str
    period_end: str
    title: str
    executive_summary: str
    signals: tuple[IntelligenceSignal, ...] = ()
    cross_signals: tuple[CrossSignal, ...] = ()
    memory_links: tuple[str, ...] = ()
    synthesis_metadata: SynthesisMetadata = field(default_factory=SynthesisMetadata)
    delivery_hints: DeliveryHints = field(default_factory=DeliveryHints)

    def validate(self) -> None:
        for name, value in (
            ("brief_type", self.brief_type),
            ("domain", self.domain),
            ("period_start", self.period_start),
            ("period_end", self.period_end),
            ("title", self.title),
            ("executive_summary", self.executive_summary),
        ):
            if not str(value).strip():
                raise ValueError(f"{name} must not be empty.")
        for signal in self.signals:
            signal.validate()
        for cross_signal in self.cross_signals:
            cross_signal.validate()

    @property
    def top_actions(self) -> tuple[str, ...]:
        return tuple(f"{signal.action}: {signal.title}" for signal in self.signals)


def signal_from_decision(decision: Decision, *, title: str | None = None, source_type: str | None = None) -> IntelligenceSignal:
    rationale = decision.rationale.strip()
    display_title = title or decision.signal_id
    source = source_type or decision.signal_id.split(":", 1)[0]
    return IntelligenceSignal(
        signal_id=decision.signal_id,
        title=display_title,
        source_type=source,
        action=decision.action,
        confidence=decision.confidence,
        rationale=rationale,
        why_now=_fallback_field("Why now", rationale),
        what_changed=_fallback_field("What changed", rationale),
        connects_to=_fallback_field("Connects to", rationale),
        what_to_do=_fallback_field("What to do", f"{decision.action} {display_title}"),
        evidence=(decision.expected_payoff, decision.risk),
    )


def brief_record_to_intelligence_brief(record: BriefRecord) -> IntelligenceBrief:
    signals = tuple(
        IntelligenceSignal(
            signal_id=f"brief-action:{index}",
            title=action.split(":", 1)[-1].strip() or action,
            source_type="brief",
            action=action.split(":", 1)[0].strip() if ":" in action else "Watch",
            confidence="medium",
            rationale=action,
            why_now=_fallback_field("Why now", action),
            what_changed=_fallback_field("What changed", action),
            connects_to="Prior memory and current reporting window.",
            what_to_do=action,
        )
        for index, action in enumerate(record.top_actions, start=1)
    )
    brief = IntelligenceBrief(
        brief_type=record.brief_type,
        domain=record.domain,
        period_start=record.period_start,
        period_end=record.period_end,
        title=record.title,
        executive_summary=record.executive_summary,
        signals=signals,
        memory_links=(record.id,),
        delivery_hints=DeliveryHints(
            primary_publisher="notion" if record.notion_status == "published" else "obsidian",
            requested_publishers=tuple(
                channel
                for channel, status in (
                    ("notion", record.notion_status),
                    ("telegram", record.telegram_status),
                )
                if status not in {"dry-run", "skipped"}
            )
            or ("obsidian",),
        ),
    )
    brief.validate()
    return brief


def top_actions_to_intelligence_brief(
    *,
    brief_type: str,
    domain: str,
    period_start: str,
    period_end: str,
    title: str,
    executive_summary: str,
    top_actions: tuple[str, ...],
    synthesis_metadata: SynthesisMetadata | None = None,
) -> IntelligenceBrief:
    signals = tuple(
        _signal_from_top_action(action, index=index)
        for index, action in enumerate(top_actions, start=1)
        if action.strip()
    )
    brief = IntelligenceBrief(
        brief_type=brief_type,
        domain=domain,
        period_start=period_start,
        period_end=period_end,
        title=title,
        executive_summary=executive_summary,
        signals=signals,
        synthesis_metadata=synthesis_metadata or SynthesisMetadata(),
    )
    brief.validate()
    return brief


def _fallback_field(label: str, value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        return f"{label}: unavailable."
    return cleaned[:500]


def _signal_from_top_action(action: str, *, index: int) -> IntelligenceSignal:
    clean = " ".join(action.split())
    if ":" in clean:
        action_name, title = clean.split(":", 1)
        action_name = action_name.strip() or "Watch"
        title = title.strip() or clean
    else:
        action_name = "Watch"
        title = clean
    return IntelligenceSignal(
        signal_id=f"top-action:{index}",
        title=title,
        source_type="memory",
        action=action_name,
        confidence="medium",
        rationale=clean,
        why_now=_fallback_field("Why now", clean),
        what_changed=_fallback_field("What changed", clean),
        connects_to="Accumulated Hermes memory for the reporting period.",
        what_to_do=clean,
    )
