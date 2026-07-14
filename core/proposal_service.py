from __future__ import annotations

from dataclasses import dataclass

from core.canonical_knowledge import CanonicalKnowledgeRepository
from core.memory import MemoryStore
from core.proposal_gate import ProposalGate, ProposalValidationContext, required_manual_acceptance_gate
from core.proposal_store import SQLiteProposalStore
from core.proposals import (
    EntityProposalPayload,
    Proposal,
    ProposalMetrics,
    RelationshipProposalPayload,
)


@dataclass(frozen=True)
class ProposalProcessResult:
    proposal: Proposal
    canonical_id: str = ""
    created: bool = False
    updated: bool = False


class ProposalTrustService:
    def __init__(
        self,
        *,
        store: MemoryStore,
        proposals: SQLiteProposalStore | None = None,
        gate: ProposalGate | None = None,
        canonical: CanonicalKnowledgeRepository | None = None,
    ) -> None:
        self.store = store
        self.proposals = proposals or SQLiteProposalStore.from_memory_store(store)
        self.gate = gate or ProposalGate()
        self.canonical = canonical or CanonicalKnowledgeRepository(store)

    def submit(self, proposal: Proposal) -> ProposalProcessResult:
        persisted = self.proposals.create(proposal)
        if persisted.validation_status == "accepted" and persisted.accepted_canonical_id:
            return ProposalProcessResult(persisted, canonical_id=persisted.accepted_canonical_id)
        result = self.gate.validate(persisted, ProposalValidationContext(self.store))
        if result.status == "rejected":
            updated = self.proposals.update_status(
                persisted.id,
                status="rejected",
                rejection_reasons=result.reasons,
                conflict_refs=result.conflict_refs,
            )
            return ProposalProcessResult(updated)
        if result.status == "needs_review":
            updated = self.proposals.update_status(
                persisted.id,
                status="needs_review",
                rejection_reasons=result.reasons,
                conflict_refs=result.conflict_refs,
            )
            return ProposalProcessResult(updated)
        canonical = self._accept_canonical(persisted)
        updated = self.proposals.update_status(
            persisted.id,
            status="accepted",
            accepted_canonical_id=canonical.canonical_id,
        )
        return ProposalProcessResult(
            updated,
            canonical_id=canonical.canonical_id,
            created=canonical.created,
            updated=canonical.updated,
        )

    def accept_needs_review(self, proposal_id: str) -> ProposalProcessResult:
        proposal = self.proposals.get(proposal_id)
        result = required_manual_acceptance_gate().validate(proposal, ProposalValidationContext(self.store))
        if result.status == "rejected":
            updated = self.proposals.update_status(
                proposal.id,
                status="rejected",
                rejection_reasons=result.reasons,
                conflict_refs=result.conflict_refs,
            )
            return ProposalProcessResult(updated)
        canonical = self._accept_canonical(proposal)
        updated = self.proposals.update_status(
            proposal.id,
            status="accepted",
            accepted_canonical_id=canonical.canonical_id,
        )
        return ProposalProcessResult(updated, canonical_id=canonical.canonical_id, created=canonical.created, updated=canonical.updated)

    def reject(self, proposal_id: str, *, reason: str) -> Proposal:
        return self.proposals.update_status(proposal_id, status="rejected", rejection_reasons=(reason,))

    def record_metrics(self, *, run_date: str, stage: str, results: tuple[ProposalProcessResult, ...]) -> ProposalMetrics:
        metrics = ProposalMetrics(
            run_date=run_date,
            stage=stage,
            proposals_created=len(results),
            proposals_accepted=sum(1 for item in results if item.proposal.validation_status == "accepted"),
            proposals_rejected=sum(1 for item in results if item.proposal.validation_status == "rejected"),
            proposals_needing_review=sum(1 for item in results if item.proposal.validation_status == "needs_review"),
            canonical_records_created=sum(1 for item in results if item.created),
            canonical_records_updated=sum(1 for item in results if item.updated),
            insight_count=sum(1 for item in results if item.canonical_id.startswith("insight:")),
        )
        self.proposals.record_metrics(metrics)
        return metrics

    def _accept_canonical(self, proposal: Proposal):
        if isinstance(proposal.payload, EntityProposalPayload):
            entity = self.store.upsert_entity(
                kind=proposal.payload.kind,
                canonical_name=proposal.payload.canonical_name,
                observed_at=proposal.payload.observed_at,
                aliases=proposal.payload.aliases,
                status=proposal.payload.status,
                tags=proposal.payload.tags,
                summary=proposal.payload.summary,
            )
            return _SimpleWriteResult(f"entity:{entity.id}", created=False, updated=True)
        if isinstance(proposal.payload, RelationshipProposalPayload):
            relationship = self.store.link_entities(
                source_entity_id=proposal.payload.source_entity_id,
                target_entity_id=proposal.payload.target_entity_id,
                relation_type=proposal.payload.relation_type,
                evidence=proposal.payload.evidence,
                confidence=proposal.payload.confidence,
            )
            return _SimpleWriteResult(f"relationship:{relationship.id}", created=False, updated=True)
        if proposal.proposal_type == "event":
            return self.canonical.accept_event(proposal)
        if proposal.proposal_type == "insight":
            return self.canonical.accept_insight(proposal)
        return _SimpleWriteResult(f"synthesis:{proposal.id}", created=True, updated=False)


@dataclass(frozen=True)
class _SimpleWriteResult:
    canonical_id: str
    created: bool
    updated: bool
