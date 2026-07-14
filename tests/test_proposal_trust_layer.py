from __future__ import annotations

from pathlib import Path

import pytest

from core.canonical_knowledge import CanonicalKnowledgeRepository
from core.memory import MemoryStore
from core.proposal_gate import (
    ConfidenceValidator,
    ConflictValidator,
    EvidenceValidator,
    ProposalGate,
    ProposalValidationContext,
    ProvenanceValidator,
    SchemaValidator,
)
from core.proposal_service import ProposalTrustService
from core.proposal_store import SQLiteProposalStore
from core.proposals import (
    EntityProposalPayload,
    InsightProposalPayload,
    Proposal,
    RelationshipProposalPayload,
)


def _insight_proposal(*, evidence_refs: tuple[str, ...] = ("observation:1",), confidence="medium") -> Proposal:
    return Proposal.create(
        proposal_type="insight",
        payload=InsightProposalPayload(
            claim="Agent tooling is converging across sources.",
            summary="GitHub, paper, and domain signals all point to agent tooling.",
            why_it_matters="Convergent signals are decision-relevant.",
            evidence_refs=evidence_refs,
            related_entity_refs=("entity:repo", "entity:paper"),
            possible_actions=("Read", "Prototype"),
            confidence=confidence,
            generated_at="2026-07-10",
        ),
        evidence_refs=evidence_refs,
        confidence=confidence,
        proposed_by="intelligence_hub.insight_engine",
        model_provider="deterministic",
        model_name="canonical_insight_engine",
        model_version="v1",
        prompt_version="",
        created_at="2026-07-10T00:00:00+00:00",
    )


def test_proposal_model_requires_typed_valid_payload_and_provenance() -> None:
    proposal = _insight_proposal()

    assert proposal.proposal_type == "insight"
    assert proposal.payload.claim.startswith("Agent tooling")
    assert proposal.proposed_by == "intelligence_hub.insight_engine"
    assert proposal.model_provider == "deterministic"
    assert proposal.payload_hash

    with pytest.raises(ValueError, match="claim must not be empty"):
        Proposal.create(
            proposal_type="insight",
            payload={"claim": "", "summary": "x", "why_it_matters": "x", "evidence_refs": ["x"]},
            evidence_refs=("x",),
            confidence="medium",
            proposed_by="intelligence_hub.insight_engine",
        )

    with pytest.raises(ValueError, match="proposed_by"):
        Proposal.create(
            proposal_type="entity",
            payload=EntityProposalPayload(kind="topic", canonical_name="Agents", observed_at="2026-07-10"),
            evidence_refs=("source:1",),
            confidence="medium",
            proposed_by="",
        )


def test_sqlite_proposal_store_migrates_old_memory_db_and_tracks_status(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite"
    old_store = MemoryStore(db_path)
    old_store.close()

    store = MemoryStore(db_path)
    try:
        proposals = SQLiteProposalStore.from_memory_store(store)
        proposal = proposals.create(_insight_proposal())
        duplicate = proposals.create(_insight_proposal())

        assert duplicate.id == proposal.id
        assert proposals.get(proposal.id).validation_status == "pending"

        updated = proposals.update_status(
            proposal.id,
            status="rejected",
            rejection_reasons=("missing evidence",),
        )

        assert updated.validation_status == "rejected"
        assert updated.rejection_reasons == ("missing evidence",)
        assert proposals.list(status="rejected") == [updated]
    finally:
        store.close()


def test_validators_cover_schema_evidence_confidence_conflict_and_provenance(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        repo = store.upsert_entity(kind="repository", canonical_name="owner/repo", observed_at="2026-07-10")
        tech = store.upsert_entity(kind="technology", canonical_name="agents", observed_at="2026-07-10")
        store.link_entities(
            source_entity_id=repo.id,
            target_entity_id=tech.id,
            relation_type="tagged_with",
            evidence="existing evidence",
            confidence="medium",
        )
        context = ProposalValidationContext(store)

        assert SchemaValidator().validate(_insight_proposal(), context).status == "accepted"
        assert EvidenceValidator().validate(_insight_proposal(evidence_refs=()), context).status == "rejected"
        assert ConfidenceValidator().validate(_insight_proposal(confidence="low"), context).status == "rejected"

        relationship = Proposal.create(
            proposal_type="relationship",
            payload=RelationshipProposalPayload(
                source_entity_id=repo.id,
                target_entity_id=tech.id,
                relation_type="tagged_with",
                evidence="conflicting evidence",
                confidence="medium",
            ),
            evidence_refs=("relationship:evidence",),
            confidence="medium",
            proposed_by="intelligence_hub.test",
        )
        conflict = ConflictValidator().validate(relationship, context)
        assert conflict.status == "needs_review"
        assert conflict.conflict_refs

        missing_model = Proposal.create(
            proposal_type="insight",
            payload=_insight_proposal().payload,
            evidence_refs=("observation:1",),
            confidence="medium",
            proposed_by="intelligence_hub.test",
            model_provider="cloud",
            model_name="",
        )
        assert ProvenanceValidator().validate(missing_model, context).status == "rejected"
    finally:
        store.close()


def test_gate_composes_validator_results(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        gate = ProposalGate()
        accepted = gate.validate(_insight_proposal(), ProposalValidationContext(store))
        rejected = gate.validate(_insight_proposal(evidence_refs=()), ProposalValidationContext(store))

        assert accepted.status == "accepted"
        assert rejected.status == "rejected"
        assert "missing evidence_refs" in rejected.reasons
    finally:
        store.close()


def test_accepted_proposal_writes_canonical_insight_and_rejected_does_not(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        service = ProposalTrustService(store=store)
        accepted = service.submit(_insight_proposal())
        duplicate = service.submit(_insight_proposal())
        rejected = service.submit(_insight_proposal(evidence_refs=()))

        insights = CanonicalKnowledgeRepository(store).list_insights()

        assert accepted.proposal.validation_status == "accepted"
        assert accepted.canonical_id.startswith("insight:")
        assert duplicate.canonical_id == accepted.canonical_id
        assert rejected.proposal.validation_status == "rejected"
        assert len(insights) == 1
        assert insights[0].proposal_id == accepted.proposal.id
        assert insights[0].evidence_refs == ("observation:1",)
    finally:
        store.close()


def test_proposal_metrics_are_queryable(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        service = ProposalTrustService(store=store)
        first = service.submit(_insight_proposal())
        second = service.submit(_insight_proposal(evidence_refs=()))

        metrics = service.record_metrics(run_date="2026-07-10", stage="daily", results=(first, second))
        latest = SQLiteProposalStore.from_memory_store(store).latest_metrics(stage="daily")

        assert latest == metrics
        assert metrics.proposals_created == 2
        assert metrics.proposals_accepted == 1
        assert metrics.proposals_rejected == 1
        assert metrics.insight_count == 1
    finally:
        store.close()
