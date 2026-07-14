from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal


ProposalType = Literal["entity", "relationship", "event", "insight", "synthesis"]
ValidationStatus = Literal["pending", "accepted", "rejected", "needs_review"]
Confidence = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class EntityProposalPayload:
    kind: str
    canonical_name: str
    observed_at: str
    aliases: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    summary: str = ""
    status: str = "active"

    @classmethod
    def from_dict(cls, data: dict) -> "EntityProposalPayload":
        return cls(
            kind=_required(data, "kind"),
            canonical_name=_required(data, "canonical_name"),
            observed_at=_required(data, "observed_at"),
            aliases=_tuple(data.get("aliases", ())),
            tags=_tuple(data.get("tags", ())),
            summary=str(data.get("summary", "")).strip(),
            status=str(data.get("status", "active")).strip() or "active",
        )


@dataclass(frozen=True)
class RelationshipProposalPayload:
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    evidence: str
    confidence: Confidence

    @classmethod
    def from_dict(cls, data: dict) -> "RelationshipProposalPayload":
        return cls(
            source_entity_id=_required(data, "source_entity_id"),
            target_entity_id=_required(data, "target_entity_id"),
            relation_type=_required(data, "relation_type"),
            evidence=_required(data, "evidence"),
            confidence=_confidence(data.get("confidence", "medium")),
        )


@dataclass(frozen=True)
class EventProposalPayload:
    event_type: str
    title: str
    summary: str
    entity_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    occurred_at: str
    status: str = "active"

    @classmethod
    def from_dict(cls, data: dict) -> "EventProposalPayload":
        return cls(
            event_type=_required(data, "event_type"),
            title=_required(data, "title"),
            summary=_required(data, "summary"),
            entity_refs=_tuple(data.get("entity_refs", ())),
            evidence_refs=_tuple(data.get("evidence_refs", ())),
            occurred_at=_required(data, "occurred_at"),
            status=str(data.get("status", "active")).strip() or "active",
        )


@dataclass(frozen=True)
class InsightProposalPayload:
    claim: str
    summary: str
    why_it_matters: str
    evidence_refs: tuple[str, ...]
    related_entity_refs: tuple[str, ...] = ()
    related_event_refs: tuple[str, ...] = ()
    possible_actions: tuple[str, ...] = ()
    confidence: Confidence = "medium"
    generated_at: str = ""
    status: str = "active"

    @classmethod
    def from_dict(cls, data: dict) -> "InsightProposalPayload":
        return cls(
            claim=_required(data, "claim"),
            summary=_required(data, "summary"),
            why_it_matters=_required(data, "why_it_matters"),
            evidence_refs=_tuple(data.get("evidence_refs", ())),
            related_entity_refs=_tuple(data.get("related_entity_refs", ())),
            related_event_refs=_tuple(data.get("related_event_refs", ())),
            possible_actions=_tuple(data.get("possible_actions", ())),
            confidence=_confidence(data.get("confidence", "medium")),
            generated_at=str(data.get("generated_at", "")).strip() or _now_utc(),
            status=str(data.get("status", "active")).strip() or "active",
        )


@dataclass(frozen=True)
class SynthesisProposalPayload:
    subject_type: str
    subject_id: str
    content: str
    summary: str

    @classmethod
    def from_dict(cls, data: dict) -> "SynthesisProposalPayload":
        return cls(
            subject_type=_required(data, "subject_type"),
            subject_id=_required(data, "subject_id"),
            content=_required(data, "content"),
            summary=_required(data, "summary"),
        )


Payload = (
    EntityProposalPayload
    | RelationshipProposalPayload
    | EventProposalPayload
    | InsightProposalPayload
    | SynthesisProposalPayload
)


@dataclass(frozen=True)
class Proposal:
    id: str
    proposal_type: ProposalType
    payload: Payload
    evidence_refs: tuple[str, ...]
    confidence: Confidence
    proposed_by: str
    model_provider: str
    model_name: str
    model_version: str
    prompt_version: str
    created_at: str
    validation_status: ValidationStatus = "pending"
    rejection_reasons: tuple[str, ...] = ()
    conflict_refs: tuple[str, ...] = ()
    accepted_canonical_id: str = ""

    @classmethod
    def create(
        cls,
        *,
        proposal_type: ProposalType,
        payload: Payload | dict,
        evidence_refs: tuple[str, ...],
        confidence: Confidence,
        proposed_by: str,
        model_provider: str = "deterministic",
        model_name: str = "intelligence_hub",
        model_version: str = "v1",
        prompt_version: str = "",
        created_at: str | None = None,
    ) -> "Proposal":
        typed_payload = parse_payload(proposal_type, payload)
        return cls(
            id=_new_id(),
            proposal_type=proposal_type,
            payload=typed_payload,
            evidence_refs=tuple(ref.strip() for ref in evidence_refs if ref.strip()),
            confidence=_confidence(confidence),
            proposed_by=_clean(proposed_by),
            model_provider=model_provider.strip(),
            model_name=model_name.strip(),
            model_version=model_version.strip(),
            prompt_version=prompt_version.strip(),
            created_at=created_at or _now_utc(),
        )

    @property
    def payload_hash(self) -> str:
        body = {
            "proposal_type": self.proposal_type,
            "payload": payload_to_dict(self.payload),
            "evidence_refs": self.evidence_refs,
            "proposed_by": self.proposed_by,
        }
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProposalValidationResult:
    status: ValidationStatus
    reasons: tuple[str, ...] = ()
    conflict_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProposalMetrics:
    run_date: str
    stage: str
    proposals_created: int
    proposals_accepted: int
    proposals_rejected: int
    proposals_needing_review: int
    canonical_records_created: int
    canonical_records_updated: int
    insight_count: int


def parse_payload(proposal_type: ProposalType, payload: Payload | dict) -> Payload:
    if not isinstance(payload, dict):
        _assert_payload_type(proposal_type, payload)
        return payload
    if proposal_type == "entity":
        return EntityProposalPayload.from_dict(payload)
    if proposal_type == "relationship":
        return RelationshipProposalPayload.from_dict(payload)
    if proposal_type == "event":
        return EventProposalPayload.from_dict(payload)
    if proposal_type == "insight":
        return InsightProposalPayload.from_dict(payload)
    if proposal_type == "synthesis":
        return SynthesisProposalPayload.from_dict(payload)
    raise ValueError(f"Unsupported proposal_type: {proposal_type!r}")


def payload_to_dict(payload: Payload) -> dict:
    data = asdict(payload)
    for key, value in list(data.items()):
        if isinstance(value, tuple):
            data[key] = list(value)
    return data


def _assert_payload_type(proposal_type: ProposalType, payload: Payload) -> None:
    expected = {
        "entity": EntityProposalPayload,
        "relationship": RelationshipProposalPayload,
        "event": EventProposalPayload,
        "insight": InsightProposalPayload,
        "synthesis": SynthesisProposalPayload,
    }[proposal_type]
    if not isinstance(payload, expected):
        raise ValueError(f"{proposal_type} proposal requires {expected.__name__}.")


def _required(data: dict, key: str) -> str:
    value = str(data.get(key, "")).strip()
    if not value:
        raise ValueError(f"{key} must not be empty.")
    return value


def _tuple(value) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, (list, tuple)):
        raise ValueError("Expected a list or tuple.")
    return tuple(str(item).strip() for item in value if str(item).strip())


def _confidence(value) -> Confidence:
    cleaned = str(value).strip().lower()
    if cleaned not in {"low", "medium", "high"}:
        raise ValueError(f"Unsupported confidence: {value!r}")
    return cleaned  # type: ignore[return-value]


def _clean(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("proposed_by must not be empty.")
    return cleaned


def _new_id() -> str:
    return str(uuid.uuid4())


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
