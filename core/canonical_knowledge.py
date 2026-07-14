from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from core.memory import MemoryStore
from core.proposals import EventProposalPayload, InsightProposalPayload, Proposal, payload_to_dict


@dataclass(frozen=True)
class Event:
    id: str
    stable_key: str
    event_type: str
    title: str
    summary: str
    entity_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    occurred_at: str
    confidence: str
    status: str
    provenance: dict
    proposal_id: str


@dataclass(frozen=True)
class Insight:
    id: str
    stable_key: str
    claim: str
    summary: str
    why_it_matters: str
    evidence_refs: tuple[str, ...]
    related_entity_refs: tuple[str, ...]
    related_event_refs: tuple[str, ...]
    possible_actions: tuple[str, ...]
    confidence: str
    generated_at: str
    status: str
    provenance: dict
    proposal_id: str


@dataclass(frozen=True)
class CanonicalWriteResult:
    canonical_id: str
    created: bool
    updated: bool


def initialize_canonical_schema(store: MemoryStore) -> None:
    store._connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS canonical_events (
            id TEXT PRIMARY KEY,
            stable_key TEXT NOT NULL UNIQUE,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            entity_refs_json TEXT NOT NULL,
            evidence_refs_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            confidence TEXT NOT NULL,
            status TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            proposal_id TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS canonical_insights (
            id TEXT PRIMARY KEY,
            stable_key TEXT NOT NULL UNIQUE,
            claim TEXT NOT NULL,
            summary TEXT NOT NULL,
            why_it_matters TEXT NOT NULL,
            evidence_refs_json TEXT NOT NULL,
            related_entity_refs_json TEXT NOT NULL,
            related_event_refs_json TEXT NOT NULL,
            possible_actions_json TEXT NOT NULL,
            confidence TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            status TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            proposal_id TEXT NOT NULL
        );
        """
    )
    store._connection.commit()


class CanonicalKnowledgeRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        initialize_canonical_schema(store)

    def accept_event(self, proposal: Proposal) -> CanonicalWriteResult:
        if not isinstance(proposal.payload, EventProposalPayload):
            raise ValueError("event proposal payload required.")
        payload = proposal.payload
        stable_key = event_stable_key(payload)
        existing = self._event_by_stable_key(stable_key)
        canonical_id = existing.id if existing else f"event:{_short_hash(stable_key)}"
        self.store._connection.execute(
            """
            INSERT INTO canonical_events (
                id, stable_key, event_type, title, summary, entity_refs_json,
                evidence_refs_json, occurred_at, confidence, status, provenance_json, proposal_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stable_key) DO UPDATE SET
                title = excluded.title,
                summary = excluded.summary,
                entity_refs_json = excluded.entity_refs_json,
                evidence_refs_json = excluded.evidence_refs_json,
                confidence = excluded.confidence,
                status = excluded.status,
                provenance_json = excluded.provenance_json,
                proposal_id = excluded.proposal_id
            """,
            (
                canonical_id,
                stable_key,
                payload.event_type,
                payload.title,
                payload.summary,
                json.dumps(payload.entity_refs),
                json.dumps(payload.evidence_refs),
                payload.occurred_at,
                proposal.confidence,
                payload.status,
                json.dumps(_provenance(proposal), sort_keys=True),
                proposal.id,
            ),
        )
        self.store._connection.commit()
        return CanonicalWriteResult(canonical_id=canonical_id, created=existing is None, updated=existing is not None)

    def accept_insight(self, proposal: Proposal) -> CanonicalWriteResult:
        if not isinstance(proposal.payload, InsightProposalPayload):
            raise ValueError("insight proposal payload required.")
        payload = proposal.payload
        stable_key = insight_stable_key(payload)
        existing = self._insight_by_stable_key(stable_key)
        canonical_id = existing.id if existing else f"insight:{_short_hash(stable_key)}"
        self.store._connection.execute(
            """
            INSERT INTO canonical_insights (
                id, stable_key, claim, summary, why_it_matters, evidence_refs_json,
                related_entity_refs_json, related_event_refs_json, possible_actions_json,
                confidence, generated_at, status, provenance_json, proposal_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stable_key) DO UPDATE SET
                summary = excluded.summary,
                why_it_matters = excluded.why_it_matters,
                evidence_refs_json = excluded.evidence_refs_json,
                related_entity_refs_json = excluded.related_entity_refs_json,
                related_event_refs_json = excluded.related_event_refs_json,
                possible_actions_json = excluded.possible_actions_json,
                confidence = excluded.confidence,
                status = excluded.status,
                provenance_json = excluded.provenance_json,
                proposal_id = excluded.proposal_id
            """,
            (
                canonical_id,
                stable_key,
                payload.claim,
                payload.summary,
                payload.why_it_matters,
                json.dumps(payload.evidence_refs),
                json.dumps(payload.related_entity_refs),
                json.dumps(payload.related_event_refs),
                json.dumps(payload.possible_actions),
                payload.confidence,
                payload.generated_at,
                payload.status,
                json.dumps(_provenance(proposal), sort_keys=True),
                proposal.id,
            ),
        )
        self.store._connection.commit()
        return CanonicalWriteResult(canonical_id=canonical_id, created=existing is None, updated=existing is not None)

    def list_events(self) -> list[Event]:
        rows = self.store._connection.execute(
            "SELECT * FROM canonical_events ORDER BY occurred_at ASC, id ASC"
        ).fetchall()
        return [_event_from_row(row) for row in rows]

    def list_insights(self) -> list[Insight]:
        rows = self.store._connection.execute(
            "SELECT * FROM canonical_insights ORDER BY generated_at ASC, id ASC"
        ).fetchall()
        return [_insight_from_row(row) for row in rows]

    def _event_by_stable_key(self, stable_key: str) -> Event | None:
        row = self.store._connection.execute(
            "SELECT * FROM canonical_events WHERE stable_key = ?",
            (stable_key,),
        ).fetchone()
        return _event_from_row(row) if row else None

    def _insight_by_stable_key(self, stable_key: str) -> Insight | None:
        row = self.store._connection.execute(
            "SELECT * FROM canonical_insights WHERE stable_key = ?",
            (stable_key,),
        ).fetchone()
        return _insight_from_row(row) if row else None


def insight_stable_key(payload: InsightProposalPayload) -> str:
    body = {
        "claim": payload.claim.casefold(),
        "related_entity_refs": sorted(payload.related_entity_refs),
    }
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


def event_stable_key(payload: EventProposalPayload) -> str:
    body = {
        "event_type": payload.event_type,
        "entity_refs": sorted(payload.entity_refs),
        "evidence_refs": sorted(payload.evidence_refs),
        "occurred_at": payload.occurred_at,
    }
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


def _provenance(proposal: Proposal) -> dict:
    return {
        "proposal_id": proposal.id,
        "proposed_by": proposal.proposed_by,
        "model_provider": proposal.model_provider,
        "model_name": proposal.model_name,
        "model_version": proposal.model_version,
        "prompt_version": proposal.prompt_version,
        "payload": payload_to_dict(proposal.payload),
    }


def _event_from_row(row) -> Event:
    return Event(
        id=str(row["id"]),
        stable_key=str(row["stable_key"]),
        event_type=str(row["event_type"]),
        title=str(row["title"]),
        summary=str(row["summary"]),
        entity_refs=tuple(json.loads(str(row["entity_refs_json"]))),
        evidence_refs=tuple(json.loads(str(row["evidence_refs_json"]))),
        occurred_at=str(row["occurred_at"]),
        confidence=str(row["confidence"]),
        status=str(row["status"]),
        provenance=json.loads(str(row["provenance_json"])),
        proposal_id=str(row["proposal_id"]),
    )


def _insight_from_row(row) -> Insight:
    return Insight(
        id=str(row["id"]),
        stable_key=str(row["stable_key"]),
        claim=str(row["claim"]),
        summary=str(row["summary"]),
        why_it_matters=str(row["why_it_matters"]),
        evidence_refs=tuple(json.loads(str(row["evidence_refs_json"]))),
        related_entity_refs=tuple(json.loads(str(row["related_entity_refs_json"]))),
        related_event_refs=tuple(json.loads(str(row["related_event_refs_json"]))),
        possible_actions=tuple(json.loads(str(row["possible_actions_json"]))),
        confidence=str(row["confidence"]),
        generated_at=str(row["generated_at"]),
        status=str(row["status"]),
        provenance=json.loads(str(row["provenance_json"])),
        proposal_id=str(row["proposal_id"]),
    )


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
