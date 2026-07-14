from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from core.memory import MemoryStore
from core.proposals import (
    Proposal,
    ProposalMetrics,
    ValidationStatus,
    parse_payload,
    payload_to_dict,
)


class ProposalRepository(Protocol):
    def create(self, proposal: Proposal) -> Proposal:
        ...

    def get(self, proposal_id: str) -> Proposal:
        ...

    def list(self, *, status: ValidationStatus | None = None) -> list[Proposal]:
        ...

    def update_status(
        self,
        proposal_id: str,
        *,
        status: ValidationStatus,
        rejection_reasons: tuple[str, ...] = (),
        conflict_refs: tuple[str, ...] = (),
        accepted_canonical_id: str = "",
    ) -> Proposal:
        ...

    def record_metrics(self, metrics: ProposalMetrics) -> None:
        ...

    def latest_metrics(self, *, stage: str | None = None) -> ProposalMetrics | None:
        ...


class SQLiteProposalStore:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        initialize_proposal_schema(store)

    @classmethod
    def open(cls, db_path: Path | str) -> "SQLiteProposalStore":
        return cls(MemoryStore(db_path))

    @classmethod
    def from_memory_store(cls, store: MemoryStore) -> "SQLiteProposalStore":
        return cls(store)

    def close(self) -> None:
        self.store.close()

    def create(self, proposal: Proposal) -> Proposal:
        row = self.store._connection.execute(
            "SELECT * FROM proposals WHERE payload_hash = ?",
            (proposal.payload_hash,),
        ).fetchone()
        if row is not None:
            return _proposal_from_row(row)
        self.store._connection.execute(
            """
            INSERT INTO proposals (
                id, proposal_type, payload_json, payload_hash, evidence_refs_json,
                confidence, proposed_by, model_provider, model_name, model_version,
                prompt_version, created_at, validation_status, rejection_reasons_json,
                conflict_refs_json, accepted_canonical_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _proposal_values(proposal),
        )
        self.store._connection.commit()
        return proposal

    def get(self, proposal_id: str) -> Proposal:
        row = self.store._connection.execute(
            "SELECT * FROM proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"Proposal not found: {proposal_id}")
        return _proposal_from_row(row)

    def list(self, *, status: ValidationStatus | None = None) -> list[Proposal]:
        if status:
            rows = self.store._connection.execute(
                "SELECT * FROM proposals WHERE validation_status = ? ORDER BY created_at ASC, id ASC",
                (status,),
            ).fetchall()
        else:
            rows = self.store._connection.execute(
                "SELECT * FROM proposals ORDER BY created_at ASC, id ASC"
            ).fetchall()
        return [_proposal_from_row(row) for row in rows]

    def update_status(
        self,
        proposal_id: str,
        *,
        status: ValidationStatus,
        rejection_reasons: tuple[str, ...] = (),
        conflict_refs: tuple[str, ...] = (),
        accepted_canonical_id: str = "",
    ) -> Proposal:
        self.store._connection.execute(
            """
            UPDATE proposals
            SET validation_status = ?,
                rejection_reasons_json = ?,
                conflict_refs_json = ?,
                accepted_canonical_id = ?
            WHERE id = ?
            """,
            (
                status,
                json.dumps(rejection_reasons),
                json.dumps(conflict_refs),
                accepted_canonical_id,
                proposal_id,
            ),
        )
        self.store._connection.commit()
        return self.get(proposal_id)

    def record_metrics(self, metrics: ProposalMetrics) -> None:
        self.store._connection.execute(
            """
            INSERT OR REPLACE INTO proposal_metrics (
                id, run_date, stage, proposals_created, proposals_accepted,
                proposals_rejected, proposals_needing_review, canonical_records_created,
                canonical_records_updated, insight_count, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                f"{metrics.stage}:{metrics.run_date}",
                metrics.run_date,
                metrics.stage,
                metrics.proposals_created,
                metrics.proposals_accepted,
                metrics.proposals_rejected,
                metrics.proposals_needing_review,
                metrics.canonical_records_created,
                metrics.canonical_records_updated,
                metrics.insight_count,
            ),
        )
        self.store._connection.commit()

    def latest_metrics(self, *, stage: str | None = None) -> ProposalMetrics | None:
        if stage:
            row = self.store._connection.execute(
                "SELECT * FROM proposal_metrics WHERE stage = ? ORDER BY created_at DESC LIMIT 1",
                (stage,),
            ).fetchone()
        else:
            row = self.store._connection.execute(
                "SELECT * FROM proposal_metrics ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return _metrics_from_row(row) if row else None


def initialize_proposal_schema(store: MemoryStore) -> None:
    store._connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS proposals (
            id TEXT PRIMARY KEY,
            proposal_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_hash TEXT NOT NULL UNIQUE,
            evidence_refs_json TEXT NOT NULL,
            confidence TEXT NOT NULL,
            proposed_by TEXT NOT NULL,
            model_provider TEXT NOT NULL,
            model_name TEXT NOT NULL,
            model_version TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            validation_status TEXT NOT NULL,
            rejection_reasons_json TEXT NOT NULL,
            conflict_refs_json TEXT NOT NULL,
            accepted_canonical_id TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS proposal_metrics (
            id TEXT PRIMARY KEY,
            run_date TEXT NOT NULL,
            stage TEXT NOT NULL,
            proposals_created INTEGER NOT NULL,
            proposals_accepted INTEGER NOT NULL,
            proposals_rejected INTEGER NOT NULL,
            proposals_needing_review INTEGER NOT NULL,
            canonical_records_created INTEGER NOT NULL,
            canonical_records_updated INTEGER NOT NULL,
            insight_count INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    store._connection.commit()


def _proposal_values(proposal: Proposal) -> tuple:
    return (
        proposal.id,
        proposal.proposal_type,
        json.dumps(payload_to_dict(proposal.payload), sort_keys=True),
        proposal.payload_hash,
        json.dumps(proposal.evidence_refs),
        proposal.confidence,
        proposal.proposed_by,
        proposal.model_provider,
        proposal.model_name,
        proposal.model_version,
        proposal.prompt_version,
        proposal.created_at,
        proposal.validation_status,
        json.dumps(proposal.rejection_reasons),
        json.dumps(proposal.conflict_refs),
        proposal.accepted_canonical_id,
    )


def _proposal_from_row(row) -> Proposal:
    proposal_type = str(row["proposal_type"])
    payload = parse_payload(proposal_type, json.loads(str(row["payload_json"])))  # type: ignore[arg-type]
    return Proposal(
        id=str(row["id"]),
        proposal_type=proposal_type,  # type: ignore[arg-type]
        payload=payload,
        evidence_refs=tuple(json.loads(str(row["evidence_refs_json"]))),
        confidence=str(row["confidence"]),  # type: ignore[arg-type]
        proposed_by=str(row["proposed_by"]),
        model_provider=str(row["model_provider"]),
        model_name=str(row["model_name"]),
        model_version=str(row["model_version"]),
        prompt_version=str(row["prompt_version"]),
        created_at=str(row["created_at"]),
        validation_status=str(row["validation_status"]),  # type: ignore[arg-type]
        rejection_reasons=tuple(json.loads(str(row["rejection_reasons_json"]))),
        conflict_refs=tuple(json.loads(str(row["conflict_refs_json"]))),
        accepted_canonical_id=str(row["accepted_canonical_id"]),
    )


def _metrics_from_row(row) -> ProposalMetrics:
    return ProposalMetrics(
        run_date=str(row["run_date"]),
        stage=str(row["stage"]),
        proposals_created=int(row["proposals_created"]),
        proposals_accepted=int(row["proposals_accepted"]),
        proposals_rejected=int(row["proposals_rejected"]),
        proposals_needing_review=int(row["proposals_needing_review"]),
        canonical_records_created=int(row["canonical_records_created"]),
        canonical_records_updated=int(row["canonical_records_updated"]),
        insight_count=int(row["insight_count"]),
    )
