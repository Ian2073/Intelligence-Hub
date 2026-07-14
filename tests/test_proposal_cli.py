from __future__ import annotations

from pathlib import Path

from core.memory import MemoryStore
from core.proposal_service import ProposalTrustService
from core.proposal_store import SQLiteProposalStore
from core.proposals import EntityProposalPayload, InsightProposalPayload, Proposal
from scripts.proposals import main


def test_proposal_cli_lists_revalidates_and_rejects(tmp_path: Path, monkeypatch, capsys) -> None:
    db_path = tmp_path / "memory.sqlite"
    monkeypatch.setenv("HERMES_MEMORY_DB", str(db_path))
    store = MemoryStore(db_path)
    try:
        result = ProposalTrustService(store=store).submit(
            Proposal.create(
                proposal_type="insight",
                payload=InsightProposalPayload(
                    claim="Needs evidence",
                    summary="No evidence.",
                    why_it_matters="No evidence.",
                    evidence_refs=(),
                    confidence="medium",
                    generated_at="2026-07-10",
                ),
                evidence_refs=(),
                confidence="medium",
                proposed_by="intelligence_hub.test",
            )
        )
        proposal_id = result.proposal.id
    finally:
        store.close()

    assert main(["list", "--status", "rejected"]) == 0
    output = capsys.readouterr().out
    assert proposal_id in output
    assert "missing evidence_refs" in output

    assert main(["revalidate", proposal_id]) == 0
    output = capsys.readouterr().out
    assert "rejected" in output

    assert main(["reject", proposal_id, "--reason", "manual audit"]) == 0
    output = capsys.readouterr().out
    assert "manual audit" in output


def test_proposal_cli_accepts_needs_review_without_bypassing_required_validation(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "memory.sqlite"
    monkeypatch.setenv("HERMES_MEMORY_DB", str(db_path))
    store = MemoryStore(db_path)
    try:
        result = ProposalTrustService(store=store).submit(
            Proposal.create(
                proposal_type="entity",
                payload=EntityProposalPayload(
                    kind="topic",
                    canonical_name="Agent tooling",
                    observed_at="2026-07-10",
                    summary="Low-confidence topic proposal.",
                ),
                evidence_refs=("source:1",),
                confidence="low",
                proposed_by="intelligence_hub.test",
            )
        )
        proposal_id = result.proposal.id
        assert result.proposal.validation_status == "needs_review"
    finally:
        store.close()

    assert main(["accept", proposal_id]) == 0
    output = capsys.readouterr().out
    assert "accepted" in output

    store = MemoryStore(db_path)
    try:
        proposal = SQLiteProposalStore.from_memory_store(store).get(proposal_id)
        assert proposal.validation_status == "accepted"
        assert proposal.accepted_canonical_id.startswith("entity:")
    finally:
        store.close()
