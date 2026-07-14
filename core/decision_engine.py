from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol

from core.intelligence_brief import RationaleFields
from core.memory import ALLOWED_DECISION_ACTIONS, DecisionAction


logger = logging.getLogger(__name__)

ACTION_RANK: dict[str, int] = {
    "Prototype": 0,
    "Implement": 0,
    "Read": 1,
    "Watch": 2,
    "Review later": 3,
    "Ignore": 4,
}


class RationaleGenerator(Protocol):
    def generate(self, prompt: str, *, tier: str = "pro") -> str:
        ...


@dataclass(frozen=True)
class DecisionCandidate:
    signal_id: str
    title: str
    source_type: str
    action: DecisionAction
    confidence: str
    evidence: tuple[str, ...] = ()
    strength: int = 0
    rationale: str = ""


@dataclass(frozen=True)
class DecisionRationale:
    text: str
    fields: RationaleFields
    generated_by: str
    fallback_used: bool = False
    fallback_reason: str = ""


class DecisionEngine:
    def __init__(self, *, top_ai_limit: int = 5) -> None:
        self.top_ai_limit = max(0, top_ai_limit)

    def action_rank(self, action: str) -> int:
        return ACTION_RANK.get(action, 9)

    def select_top(self, candidates: tuple[DecisionCandidate, ...], *, limit: int) -> tuple[DecisionCandidate, ...]:
        ranked = sorted(candidates, key=lambda item: (self.action_rank(item.action), -item.strength, item.title.casefold()))
        selected: list[DecisionCandidate] = []
        seen: set[str] = set()
        for candidate in ranked:
            identity = f"{candidate.source_type}:{candidate.title.casefold()}"
            if identity in seen:
                continue
            selected.append(candidate)
            seen.add(identity)
            if len(selected) >= limit:
                break
        return tuple(selected)

    def validate_rationale(self, fields: RationaleFields) -> bool:
        try:
            fields.validate()
        except ValueError:
            return False
        return True

    def build_rationale(
        self,
        candidate: DecisionCandidate,
        *,
        generator: RationaleGenerator | None = None,
        use_ai: bool = False,
        knowledge_context: str = "",
    ) -> DecisionRationale:
        fallback = self._deterministic_rationale(candidate)
        if not use_ai or generator is None:
            return fallback
        try:
            raw = generator.generate(_rationale_prompt(candidate, knowledge_context=knowledge_context), tier="pro")
            rationale = self._parse_ai_rationale(raw)
            if self.validate_rationale(rationale.fields):
                return rationale
            return DecisionRationale(
                text=fallback.text,
                fields=fallback.fields,
                generated_by="deterministic",
                fallback_used=True,
                fallback_reason="AI rationale failed structure validation.",
            )
        except Exception as exc:
            logger.warning("AI decision rationale failed; using deterministic fallback. Reason: %s", exc)
            logger.debug("AI decision rationale fallback traceback.", exc_info=True)
            return DecisionRationale(
                text=fallback.text,
                fields=fallback.fields,
                generated_by="deterministic",
                fallback_used=True,
                fallback_reason=str(exc)[:300] or exc.__class__.__name__,
            )

    def _deterministic_rationale(self, candidate: DecisionCandidate) -> DecisionRationale:
        evidence = "; ".join(item for item in candidate.evidence if item.strip()) or "No extra evidence was supplied."
        fields = RationaleFields(
            why_now=f"{candidate.title} is ranked as {candidate.action} based on current evidence.",
            what_changed=evidence,
            connects_to=f"This {candidate.source_type} signal connects to the active intelligence watchlist.",
            what_to_do=f"{candidate.action} {candidate.title}.",
        )
        text = (
            f"Why now: {fields.why_now} "
            f"What changed: {fields.what_changed} "
            f"Connects to: {fields.connects_to} "
            f"What to do: {fields.what_to_do}"
        )
        return DecisionRationale(text=text, fields=fields, generated_by="deterministic")

    def _parse_ai_rationale(self, raw: str) -> DecisionRationale:
        text = raw.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = _parse_labelled_text(text)
        fields = RationaleFields(
            why_now=str(data.get("why_now", "")).strip(),
            what_changed=str(data.get("what_changed", "")).strip(),
            connects_to=str(data.get("connects_to", "")).strip(),
            what_to_do=str(data.get("what_to_do", "")).strip(),
        )
        return DecisionRationale(text=text, fields=fields, generated_by="ai")


def normalize_action(action: str) -> DecisionAction:
    cleaned = action.strip()
    if cleaned not in ALLOWED_DECISION_ACTIONS:
        return "Review later"
    return cleaned  # type: ignore[return-value]


def _parse_labelled_text(text: str) -> dict[str, str]:
    labels = {
        "why_now": ("why now", "why_now"),
        "what_changed": ("what changed", "what_changed"),
        "connects_to": ("connects to", "connects_to"),
        "what_to_do": ("what to do", "what_to_do"),
    }
    lowered = text.casefold()
    result: dict[str, str] = {}
    for key, names in labels.items():
        start_positions = [lowered.find(name) for name in names if lowered.find(name) >= 0]
        if not start_positions:
            result[key] = ""
            continue
        start = min(start_positions)
        value_start = lowered.find(":", start)
        if value_start < 0:
            result[key] = ""
            continue
        next_starts = [
            lowered.find(other, value_start + 1)
            for other_names in labels.values()
            for other in other_names
            if lowered.find(other, value_start + 1) >= 0
        ]
        value_end = min(next_starts) if next_starts else len(text)
        result[key] = text[value_start + 1 : value_end].strip(" \n-")
    return result


def _rationale_prompt(candidate: DecisionCandidate, *, knowledge_context: str = "") -> str:
    evidence = "\n".join(f"- {item}" for item in candidate.evidence[:8])
    knowledge = f"\nKnowledge context:\n{knowledge_context}\n" if knowledge_context.strip() else ""
    return f"""Return JSON with keys why_now, what_changed, connects_to, what_to_do.

Signal: {candidate.title}
Source: {candidate.source_type}
Action: {candidate.action}
Confidence: {candidate.confidence}
{knowledge}
Evidence:
{evidence}
"""
