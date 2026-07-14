from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from core.intelligence_brief import IntelligenceBrief
from core.memory import BriefRecord, MemoryStore
from core.canonical_knowledge import initialize_canonical_schema
from core.proposal_store import initialize_proposal_schema


SCHEMA_VERSION = "3"


@dataclass(frozen=True)
class MemoryStats:
    db_path: Path
    db_size_bytes: int
    schema_version: str
    table_rows: dict[str, int]


class MemoryEngine:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self.initialize_phase2_schema()

    @classmethod
    def open(cls, db_path: Path | str) -> "MemoryEngine":
        return cls(MemoryStore(db_path))

    def close(self) -> None:
        self.store.close()

    def initialize_phase2_schema(self) -> None:
        connection = self.store._connection
        initialize_canonical_schema(self.store)
        initialize_proposal_schema(self.store)
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS synthesis_metadata (
                id TEXT PRIMARY KEY,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_observations_entity_observed
                ON observations(entity_id, observed_at);
            CREATE INDEX IF NOT EXISTS idx_decisions_revisit_date
                ON decisions(revisit_date);
            """
        )
        connection.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('schema_version', ?)",
            (SCHEMA_VERSION,),
        )
        connection.commit()

    @contextmanager
    def batch(self) -> Iterator[MemoryStore]:
        connection = self.store._connection
        try:
            connection.execute("BEGIN")
            yield self.store
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()

    def record_brief(self, brief: IntelligenceBrief, *, notion_status: str = "dry-run", notion_url: str = "", telegram_status: str = "dry-run", telegram_detail: str = "") -> BriefRecord:
        brief.validate()
        record = self.store.record_brief(
            brief_type=brief.brief_type,
            domain=brief.domain,
            period_start=brief.period_start,
            period_end=brief.period_end,
            title=brief.title,
            executive_summary=brief.executive_summary,
            top_actions=brief.top_actions,
            notion_status=notion_status,
            notion_url=notion_url,
            telegram_status=telegram_status,
            telegram_detail=telegram_detail,
        )
        self.record_synthesis_metadata("brief", record.id, brief.synthesis_metadata.as_dict())
        return record

    def record_synthesis_metadata(self, subject_type: str, subject_id: str, metadata: dict) -> None:
        connection = self.store._connection
        connection.execute(
            """
            INSERT INTO synthesis_metadata (id, subject_type, subject_id, metadata_json, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (
                f"{subject_type}:{subject_id}",
                subject_type,
                subject_id,
                json.dumps(metadata, sort_keys=True),
            ),
        )
        connection.commit()

    def schema_version(self) -> str:
        row = self.store._connection.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        ).fetchone()
        return str(row["value"]) if row is not None else "1"

    def stats(self) -> MemoryStats:
        path = self.store.db_path
        size = path.stat().st_size if path.exists() else 0
        return MemoryStats(
            db_path=path,
            db_size_bytes=size,
            schema_version=self.schema_version(),
            table_rows=self.store.get_table_stats(),
        )
