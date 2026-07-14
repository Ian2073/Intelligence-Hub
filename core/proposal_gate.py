from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.canonical_knowledge import CanonicalKnowledgeRepository, insight_stable_key
from core.memory import MemoryStore
from core.proposals import (
    EventProposalPayload,
    InsightProposalPayload,
    Proposal,
    ProposalValidationResult,
    RelationshipProposalPayload,
    ValidationStatus,
    parse_payload,
)


class ProposalValidator(Protocol):
    def validate(self, proposal: Proposal, context: "ProposalValidationContext") -> ProposalValidationResult:
        ...


@dataclass(frozen=True)
class ProposalValidationContext:
    store: MemoryStore


class SchemaValidator:
    def validate(self, proposal: Proposal, context: ProposalValidationContext) -> ProposalValidationResult:
        try:
            parse_payload(proposal.proposal_type, proposal.payload)
        except Exception as exc:
            return ProposalValidationResult("rejected", (f"invalid schema: {exc}",))
        return ProposalValidationResult("accepted")


class EvidenceValidator:
    def validate(self, proposal: Proposal, context: ProposalValidationContext) -> ProposalValidationResult:
        evidence_refs = proposal.evidence_refs
        if isinstance(proposal.payload, (InsightProposalPayload, EventProposalPayload)):
            evidence_refs = tuple(dict.fromkeys((*evidence_refs, *proposal.payload.evidence_refs)))
        if not evidence_refs:
            return ProposalValidationResult("rejected", ("missing evidence_refs",))
        return ProposalValidationResult("accepted")


class ConfidenceValidator:
    def validate(self, proposal: Proposal, context: ProposalValidationContext) -> ProposalValidationResult:
        if proposal.confidence == "low":
            if proposal.proposal_type in {"entity", "synthesis"}:
                return ProposalValidationResult("needs_review", ("low confidence",))
            return ProposalValidationResult("rejected", ("low confidence",))
        return ProposalValidationResult("accepted")


class ConflictValidator:
    def validate(self, proposal: Proposal, context: ProposalValidationContext) -> ProposalValidationResult:
        if isinstance(proposal.payload, RelationshipProposalPayload):
            rows = context.store._connection.execute(
                """
                SELECT id, evidence
                FROM entity_relationships
                WHERE source_entity_id = ? AND target_entity_id = ? AND relation_type = ?
                """,
                (
                    proposal.payload.source_entity_id,
                    proposal.payload.target_entity_id,
                    proposal.payload.relation_type,
                ),
            ).fetchall()
            conflicts = tuple(str(row["id"]) for row in rows if str(row["evidence"]) != proposal.payload.evidence)
            if conflicts:
                return ProposalValidationResult("needs_review", ("conflicting relationship evidence",), conflicts)
        if isinstance(proposal.payload, InsightProposalPayload):
            existing = CanonicalKnowledgeRepository(context.store)._insight_by_stable_key(
                insight_stable_key(proposal.payload)
            )
            if existing and existing.claim != proposal.payload.claim:
                return ProposalValidationResult("needs_review", ("conflicting insight claim",), (existing.id,))
        return ProposalValidationResult("accepted")


class ProvenanceValidator:
    def validate(self, proposal: Proposal, context: ProposalValidationContext) -> ProposalValidationResult:
        if not proposal.proposed_by:
            return ProposalValidationResult("rejected", ("missing proposed_by",))
        if proposal.model_provider and not proposal.model_name:
            return ProposalValidationResult("rejected", ("missing model_name",))
        if proposal.proposed_by.startswith("hermes") and proposal.model_provider == "":
            return ProposalValidationResult("needs_review", ("hermes proposal missing model provider",))
        return ProposalValidationResult("accepted")


class ProposalGate:
    def __init__(self, validators: tuple[ProposalValidator, ...] | None = None) -> None:
        self.validators = validators or (
            SchemaValidator(),
            EvidenceValidator(),
            ConfidenceValidator(),
            ConflictValidator(),
            ProvenanceValidator(),
        )

    def validate(self, proposal: Proposal, context: ProposalValidationContext) -> ProposalValidationResult:
        statuses: list[ValidationStatus] = []
        reasons: list[str] = []
        conflict_refs: list[str] = []
        for validator in self.validators:
            result = validator.validate(proposal, context)
            statuses.append(result.status)
            reasons.extend(result.reasons)
            conflict_refs.extend(result.conflict_refs)
            if result.status == "rejected":
                return ProposalValidationResult("rejected", tuple(reasons), tuple(conflict_refs))
        if "needs_review" in statuses:
            return ProposalValidationResult("needs_review", tuple(reasons), tuple(conflict_refs))
        return ProposalValidationResult("accepted", tuple(reasons), tuple(conflict_refs))


def required_manual_acceptance_gate() -> ProposalGate:
    return ProposalGate((SchemaValidator(), EvidenceValidator(), ProvenanceValidator()))
