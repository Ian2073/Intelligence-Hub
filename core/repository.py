from __future__ import annotations

from pathlib import Path
from typing import Protocol

from core.canonical_knowledge import CanonicalKnowledgeRepository, Event, Insight
from core.memory import BriefRecord, Decision, Entity, EntityRelationship, MemoryStore, Observation, RunRecord
from core.proposal_store import SQLiteProposalStore
from core.proposals import Proposal, ValidationStatus


class Repository(Protocol):
    def list_entities(self, *, kind: str | None = None, tag: str | None = None) -> list[Entity]:
        ...

    def list_observations(self, *, since: str | None = None, until: str | None = None) -> list[Observation]:
        ...

    def list_relationships(self, *, source_entity_id: str | None = None) -> list[EntityRelationship]:
        ...

    def list_decisions(self, *, since: str | None = None, until: str | None = None) -> list[Decision]:
        ...

    def list_briefs(
        self,
        *,
        brief_type: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> list[BriefRecord]:
        ...

    def list_runs(self, *, since: str | None = None, until: str | None = None) -> list[RunRecord]:
        ...

    def list_events(self) -> list[Event]:
        ...

    def list_insights(self) -> list[Insight]:
        ...

    def list_proposals(self, *, status: ValidationStatus | None = None) -> list[Proposal]:
        ...


class SQLiteRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self.canonical = CanonicalKnowledgeRepository(store)
        self.proposals = SQLiteProposalStore.from_memory_store(store)

    @classmethod
    def open(cls, db_path: Path | str) -> "SQLiteRepository":
        return cls(MemoryStore(db_path))

    @classmethod
    def from_memory_store(cls, store: MemoryStore) -> "SQLiteRepository":
        return cls(store)

    def close(self) -> None:
        self.store.close()

    def list_entities(self, *, kind: str | None = None, tag: str | None = None) -> list[Entity]:
        return self.store.list_entities(kind=kind, tag=tag)

    def list_observations(self, *, since: str | None = None, until: str | None = None) -> list[Observation]:
        return self.store.list_observations(since=since, until=until)

    def list_relationships(self, *, source_entity_id: str | None = None) -> list[EntityRelationship]:
        return self.store.list_relationships(source_entity_id=source_entity_id)

    def list_decisions(self, *, since: str | None = None, until: str | None = None) -> list[Decision]:
        return self.store.list_decisions(since=since, until=until)

    def list_briefs(
        self,
        *,
        brief_type: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> list[BriefRecord]:
        return self.store.list_briefs(brief_type=brief_type, since=since, until=until)

    def list_runs(self, *, since: str | None = None, until: str | None = None) -> list[RunRecord]:
        return self.store.list_runs(since=since, until=until)

    def list_events(self) -> list[Event]:
        return self.canonical.list_events()

    def list_insights(self) -> list[Insight]:
        return self.canonical.list_insights()

    def list_proposals(self, *, status: ValidationStatus | None = None) -> list[Proposal]:
        return self.proposals.list(status=status)
