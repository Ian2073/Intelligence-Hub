from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


DecisionAction = Literal["Ignore", "Watch", "Read", "Prototype", "Implement", "Review later"]

ALLOWED_DECISION_ACTIONS: frozenset[str] = frozenset(
    {"Ignore", "Watch", "Read", "Prototype", "Implement", "Review later"}
)


@dataclass(frozen=True)
class Entity:
    id: str
    kind: str
    canonical_name: str
    aliases: tuple[str, ...]
    first_seen: str
    last_seen: str
    status: str
    tags: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Observation:
    id: str
    entity_id: str
    observed_at: str
    source_type: str
    source_url: str
    metric_name: str
    previous_value: str
    current_value: str
    raw_evidence: str
    confidence: str


@dataclass(frozen=True)
class EntityRelationship:
    id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    evidence: str
    confidence: str


@dataclass(frozen=True)
class Decision:
    id: str
    signal_id: str
    action: DecisionAction
    rationale: str
    expected_payoff: str
    risk: str
    revisit_date: str
    confidence: str


@dataclass(frozen=True)
class BriefRecord:
    id: str
    brief_type: str
    domain: str
    period_start: str
    period_end: str
    title: str
    executive_summary: str
    top_actions: tuple[str, ...]
    notion_status: str
    notion_url: str
    telegram_status: str
    telegram_detail: str


@dataclass(frozen=True)
class RunRecord:
    id: str
    run_date: str
    stage: str
    title: str
    period_start: str
    period_end: str
    status: str
    notion_status: str
    notion_url: str
    telegram_status: str
    telegram_detail: str
    created_at: str


@dataclass(frozen=True)
class NotificationOutboxRecord:
    id: str
    title: str
    decisions: tuple[str, ...]
    top_action: str
    notion_url: str
    status: str
    attempts: int
    last_error: str
    created_at: str
    sent_at: str


class MemoryStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        self.initialize()

    def close(self) -> None:
        self._connection.close()

    def initialize(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                canonical_name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                aliases_json TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                status TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                summary TEXT NOT NULL,
                UNIQUE(kind, normalized_name)
            );

            CREATE TABLE IF NOT EXISTS entity_aliases (
                entity_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                alias TEXT NOT NULL,
                normalized_alias TEXT NOT NULL,
                PRIMARY KEY(kind, normalized_alias),
                FOREIGN KEY(entity_id) REFERENCES entities(id)
            );

            CREATE TABLE IF NOT EXISTS observations (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                previous_value TEXT NOT NULL,
                current_value TEXT NOT NULL,
                raw_evidence TEXT NOT NULL,
                confidence TEXT NOT NULL,
                FOREIGN KEY(entity_id) REFERENCES entities(id)
            );

            CREATE TABLE IF NOT EXISTS entity_relationships (
                id TEXT PRIMARY KEY,
                source_entity_id TEXT NOT NULL,
                target_entity_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                evidence TEXT NOT NULL,
                confidence TEXT NOT NULL,
                UNIQUE(source_entity_id, target_entity_id, relation_type),
                FOREIGN KEY(source_entity_id) REFERENCES entities(id),
                FOREIGN KEY(target_entity_id) REFERENCES entities(id)
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                signal_id TEXT NOT NULL,
                action TEXT NOT NULL,
                rationale TEXT NOT NULL,
                expected_payoff TEXT NOT NULL,
                risk TEXT NOT NULL,
                revisit_date TEXT NOT NULL,
                confidence TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS briefs (
                id TEXT PRIMARY KEY,
                brief_type TEXT NOT NULL,
                domain TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                title TEXT NOT NULL,
                executive_summary TEXT NOT NULL,
                top_actions_json TEXT NOT NULL,
                notion_status TEXT NOT NULL,
                notion_url TEXT NOT NULL,
                telegram_status TEXT NOT NULL,
                telegram_detail TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runtime_runs (
                id TEXT PRIMARY KEY,
                run_date TEXT NOT NULL,
                stage TEXT NOT NULL,
                title TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                status TEXT NOT NULL,
                notion_status TEXT NOT NULL,
                notion_url TEXT NOT NULL,
                telegram_status TEXT NOT NULL,
                telegram_detail TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notification_outbox (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                decisions_json TEXT NOT NULL,
                top_action TEXT NOT NULL,
                notion_url TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                last_error TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sent_at TEXT NOT NULL
            );
            """
        )
        self._connection.commit()

    def upsert_entity(
        self,
        *,
        kind: str,
        canonical_name: str,
        observed_at: str,
        aliases: tuple[str, ...] = (),
        status: str = "active",
        tags: tuple[str, ...] = (),
        summary: str = "",
    ) -> Entity:
        clean_kind = _required(kind, "kind")
        clean_name = _required(canonical_name, "canonical_name")
        clean_seen = _required(observed_at, "observed_at")
        normalized_aliases = _normalized_values((clean_name, *aliases))

        existing = self.find_entity(kind=clean_kind, canonical_name=clean_name, aliases=aliases)
        if existing is None:
            entity = Entity(
                id=_new_id(),
                kind=clean_kind,
                canonical_name=clean_name,
                aliases=tuple(normalized_aliases.keys()),
                first_seen=clean_seen,
                last_seen=clean_seen,
                status=_optional(status, "active"),
                tags=tuple(_normalized_values(tags).keys()),
                summary=summary.strip(),
            )
            self._insert_entity(entity)
            return entity

        merged_aliases = tuple(_normalized_values((*existing.aliases, clean_name, *aliases)).keys())
        merged_tags = tuple(_normalized_values((*existing.tags, *tags)).keys())
        updated = Entity(
            id=existing.id,
            kind=existing.kind,
            canonical_name=existing.canonical_name,
            aliases=merged_aliases,
            first_seen=min(existing.first_seen, clean_seen),
            last_seen=max(existing.last_seen, clean_seen),
            status=_optional(status, existing.status),
            tags=merged_tags,
            summary=summary.strip() or existing.summary,
        )
        self._update_entity(updated)
        return updated

    def find_entity(
        self,
        *,
        kind: str,
        canonical_name: str,
        aliases: tuple[str, ...] = (),
    ) -> Entity | None:
        clean_kind = _required(kind, "kind")
        candidates = _normalized_values((canonical_name, *aliases))
        for normalized in candidates.values():
            row = self._connection.execute(
                """
                SELECT e.*
                FROM entity_aliases a
                JOIN entities e ON e.id = a.entity_id
                WHERE a.kind = ? AND a.normalized_alias = ?
                LIMIT 1
                """,
                (clean_kind, normalized),
            ).fetchone()
            if row is not None:
                return _entity_from_row(row)
        return None

    def record_observation(
        self,
        *,
        entity_id: str,
        observed_at: str,
        source_type: str,
        source_url: str,
        metric_name: str,
        previous_value: object,
        current_value: object,
        raw_evidence: str,
        confidence: str,
    ) -> Observation:
        observation = Observation(
            id=_new_id(),
            entity_id=_required(entity_id, "entity_id"),
            observed_at=_required(observed_at, "observed_at"),
            source_type=_required(source_type, "source_type"),
            source_url=_required(source_url, "source_url"),
            metric_name=_required(metric_name, "metric_name"),
            previous_value=str(previous_value),
            current_value=str(current_value),
            raw_evidence=_required(raw_evidence, "raw_evidence"),
            confidence=_required(confidence, "confidence"),
        )
        self._connection.execute(
            """
            INSERT INTO observations (
                id, entity_id, observed_at, source_type, source_url, metric_name,
                previous_value, current_value, raw_evidence, confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation.id,
                observation.entity_id,
                observation.observed_at,
                observation.source_type,
                observation.source_url,
                observation.metric_name,
                observation.previous_value,
                observation.current_value,
                observation.raw_evidence,
                observation.confidence,
            ),
        )
        self._connection.commit()
        return observation

    def get_entity_history(self, entity_id: str, since: str | None = None) -> list[Observation]:
        clean_entity_id = _required(entity_id, "entity_id")
        if since:
            rows = self._connection.execute(
                """
                SELECT *
                FROM observations
                WHERE entity_id = ? AND observed_at >= ?
                ORDER BY observed_at ASC, id ASC
                """,
                (clean_entity_id, since),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT *
                FROM observations
                WHERE entity_id = ?
                ORDER BY observed_at ASC, id ASC
                """,
                (clean_entity_id,),
            ).fetchall()
        return [_observation_from_row(row) for row in rows]

    def list_observations(self, *, since: str | None = None, until: str | None = None) -> list[Observation]:
        clauses: list[str] = []
        params: list[str] = []
        if since:
            clauses.append("observed_at >= ?")
            params.append(since)
        if until:
            clauses.append("observed_at <= ?")
            params.append(until)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"""
            SELECT *
            FROM observations
            {where}
            ORDER BY observed_at ASC, id ASC
            """,
            tuple(params),
        ).fetchall()
        return [_observation_from_row(row) for row in rows]

    def list_entities(self, *, kind: str | None = None, tag: str | None = None) -> list[Entity]:
        clauses: list[str] = []
        params: list[str] = []
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"""
            SELECT *
            FROM entities
            {where}
            ORDER BY last_seen DESC, canonical_name ASC
            """,
            tuple(params),
        ).fetchall()
        entities = [_entity_from_row(row) for row in rows]
        if tag:
            return [entity for entity in entities if tag in entity.tags]
        return entities

    def list_relationships(self, *, source_entity_id: str | None = None) -> list[EntityRelationship]:
        clauses: list[str] = []
        params: list[str] = []
        if source_entity_id:
            clauses.append("source_entity_id = ?")
            params.append(source_entity_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"""
            SELECT *
            FROM entity_relationships
            {where}
            ORDER BY relation_type ASC, id ASC
            """,
            tuple(params),
        ).fetchall()
        return [_relationship_from_row(row) for row in rows]

    def list_decisions(self, *, since: str | None = None, until: str | None = None) -> list[Decision]:
        rows = self._connection.execute(
            """
            SELECT *
            FROM decisions
            ORDER BY revisit_date ASC, id ASC
            """
        ).fetchall()
        decisions = [_decision_from_row(row) for row in rows]
        if since:
            decisions = [decision for decision in decisions if decision.revisit_date >= since]
        if until:
            decisions = [decision for decision in decisions if decision.revisit_date <= until]
        return decisions

    def link_entities(
        self,
        *,
        source_entity_id: str,
        target_entity_id: str,
        relation_type: str,
        evidence: str,
        confidence: str,
    ) -> EntityRelationship:
        relationship_id = _new_id()
        source_id = _required(source_entity_id, "source_entity_id")
        target_id = _required(target_entity_id, "target_entity_id")
        relation = _required(relation_type, "relation_type")
        self._connection.execute(
            """
            INSERT OR IGNORE INTO entity_relationships (
                id, source_entity_id, target_entity_id, relation_type, evidence, confidence
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                relationship_id,
                source_id,
                target_id,
                relation,
                _required(evidence, "evidence"),
                _required(confidence, "confidence"),
            ),
        )
        self._connection.commit()
        row = self._connection.execute(
            """
            SELECT *
            FROM entity_relationships
            WHERE source_entity_id = ? AND target_entity_id = ? AND relation_type = ?
            """,
            (source_id, target_id, relation),
        ).fetchone()
        if row is None:
            raise RuntimeError("Relationship insert failed.")
        return _relationship_from_row(row)

    def record_decision(
        self,
        *,
        signal_id: str,
        action: DecisionAction,
        rationale: str,
        expected_payoff: str,
        risk: str,
        revisit_date: str,
        confidence: str,
    ) -> Decision:
        if action not in ALLOWED_DECISION_ACTIONS:
            raise ValueError(f"Unsupported decision action: {action!r}")
        decision = Decision(
            id=_new_id(),
            signal_id=_required(signal_id, "signal_id"),
            action=action,
            rationale=_required(rationale, "rationale"),
            expected_payoff=_required(expected_payoff, "expected_payoff"),
            risk=_required(risk, "risk"),
            revisit_date=_required(revisit_date, "revisit_date"),
            confidence=_required(confidence, "confidence"),
        )
        self._connection.execute(
            """
            INSERT INTO decisions (
                id, signal_id, action, rationale, expected_payoff, risk, revisit_date, confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision.id,
                decision.signal_id,
                decision.action,
                decision.rationale,
                decision.expected_payoff,
                decision.risk,
                decision.revisit_date,
                decision.confidence,
            ),
        )
        self._connection.commit()
        return decision

    def record_brief(
        self,
        *,
        brief_type: str,
        domain: str,
        period_start: str,
        period_end: str,
        title: str,
        executive_summary: str,
        top_actions: tuple[str, ...],
        notion_status: str,
        notion_url: str,
        telegram_status: str,
        telegram_detail: str,
    ) -> BriefRecord:
        brief = BriefRecord(
            id=_new_id(),
            brief_type=_required(brief_type, "brief_type"),
            domain=_required(domain, "domain"),
            period_start=_required(period_start, "period_start"),
            period_end=_required(period_end, "period_end"),
            title=_required(title, "title"),
            executive_summary=_required(executive_summary, "executive_summary"),
            top_actions=tuple(action.strip() for action in top_actions if action.strip()),
            notion_status=_required(notion_status, "notion_status"),
            notion_url=notion_url.strip(),
            telegram_status=_required(telegram_status, "telegram_status"),
            telegram_detail=telegram_detail.strip(),
        )
        self._connection.execute(
            """
            INSERT INTO briefs (
                id, brief_type, domain, period_start, period_end, title, executive_summary,
                top_actions_json, notion_status, notion_url, telegram_status, telegram_detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                brief.id,
                brief.brief_type,
                brief.domain,
                brief.period_start,
                brief.period_end,
                brief.title,
                brief.executive_summary,
                json.dumps(brief.top_actions),
                brief.notion_status,
                brief.notion_url,
                brief.telegram_status,
                brief.telegram_detail,
            ),
        )
        self._connection.commit()
        return brief

    def list_briefs(
        self,
        *,
        brief_type: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> list[BriefRecord]:
        clauses: list[str] = []
        params: list[str] = []
        if brief_type:
            clauses.append("brief_type = ?")
            params.append(brief_type)
        if since:
            clauses.append("period_end >= ?")
            params.append(since)
        if until:
            clauses.append("period_start <= ?")
            params.append(until)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"""
            SELECT *
            FROM briefs
            {where}
            ORDER BY period_start ASC, id ASC
            """,
            tuple(params),
        ).fetchall()
        return [_brief_from_row(row) for row in rows]

    def record_run(
        self,
        *,
        run_date: str,
        stage: str,
        title: str,
        period_start: str,
        period_end: str,
        status: str,
        notion_status: str,
        notion_url: str,
        telegram_status: str,
        telegram_detail: str,
        created_at: str | None = None,
    ) -> RunRecord:
        run = RunRecord(
            id=_new_id(),
            run_date=_required(run_date, "run_date"),
            stage=_required(stage, "stage"),
            title=_required(title, "title"),
            period_start=_required(period_start, "period_start"),
            period_end=_required(period_end, "period_end"),
            status=_required(status, "status"),
            notion_status=_required(notion_status, "notion_status"),
            notion_url=notion_url.strip(),
            telegram_status=_required(telegram_status, "telegram_status"),
            telegram_detail=telegram_detail.strip(),
            created_at=created_at.strip() if created_at and created_at.strip() else _now_utc(),
        )
        self._connection.execute(
            """
            INSERT INTO runtime_runs (
                id, run_date, stage, title, period_start, period_end, status,
                notion_status, notion_url, telegram_status, telegram_detail, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.id,
                run.run_date,
                run.stage,
                run.title,
                run.period_start,
                run.period_end,
                run.status,
                run.notion_status,
                run.notion_url,
                run.telegram_status,
                run.telegram_detail,
                run.created_at,
            ),
        )
        self._connection.commit()
        return run

    def list_runs(
        self,
        *,
        stage: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> list[RunRecord]:
        clauses: list[str] = []
        params: list[str] = []
        if stage:
            clauses.append("stage = ?")
            params.append(stage)
        if since:
            clauses.append("run_date >= ?")
            params.append(since)
        if until:
            clauses.append("run_date <= ?")
            params.append(until)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"""
            SELECT *
            FROM runtime_runs
            {where}
            ORDER BY created_at ASC, id ASC
            """,
            tuple(params),
        ).fetchall()
        return [_run_from_row(row) for row in rows]

    def get_table_stats(self) -> dict[str, int]:
        tables = (
            "entities",
            "observations",
            "entity_relationships",
            "decisions",
            "briefs",
            "runtime_runs",
            "notification_outbox",
            "proposals",
            "proposal_metrics",
            "canonical_events",
            "canonical_insights",
        )
        stats: dict[str, int] = {}
        for table in tables:
            row = self._connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table,),
            ).fetchone()
            if row is None:
                stats[table] = 0
                continue
            row = self._connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
            stats[table] = int(row["count"]) if row is not None else 0
        return stats

    def enqueue_notification(
        self,
        *,
        title: str,
        decisions: tuple[str, ...],
        top_action: str,
        notion_url: str,
        last_error: str,
        created_at: str | None = None,
    ) -> NotificationOutboxRecord:
        record = NotificationOutboxRecord(
            id=_new_id(),
            title=_required(title, "title"),
            decisions=tuple(decision.strip() for decision in decisions if decision.strip()),
            top_action=_required(top_action, "top_action"),
            notion_url=_required(notion_url, "notion_url"),
            status="pending",
            attempts=0,
            last_error=last_error.strip(),
            created_at=created_at.strip() if created_at and created_at.strip() else _now_utc(),
            sent_at="",
        )
        self._connection.execute(
            """
            INSERT INTO notification_outbox (
                id, title, decisions_json, top_action, notion_url, status,
                attempts, last_error, created_at, sent_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.title,
                json.dumps(record.decisions),
                record.top_action,
                record.notion_url,
                record.status,
                record.attempts,
                record.last_error,
                record.created_at,
                record.sent_at,
            ),
        )
        self._connection.commit()
        return record

    def list_notification_outbox(self, *, status: str | None = None) -> list[NotificationOutboxRecord]:
        clauses: list[str] = []
        params: list[str] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"""
            SELECT *
            FROM notification_outbox
            {where}
            ORDER BY created_at ASC, id ASC
            """,
            tuple(params),
        ).fetchall()
        return [_notification_outbox_from_row(row) for row in rows]

    def mark_notification_sent(self, notification_id: str, *, sent_at: str | None = None) -> NotificationOutboxRecord:
        clean_id = _required(notification_id, "notification_id")
        self._connection.execute(
            """
            UPDATE notification_outbox
            SET status = 'sent', sent_at = ?, last_error = ''
            WHERE id = ?
            """,
            (sent_at.strip() if sent_at and sent_at.strip() else _now_utc(), clean_id),
        )
        self._connection.commit()
        return self._get_notification_outbox(clean_id)

    def mark_notification_failed(self, notification_id: str, *, error: str) -> NotificationOutboxRecord:
        clean_id = _required(notification_id, "notification_id")
        self._connection.execute(
            """
            UPDATE notification_outbox
            SET status = 'pending', attempts = attempts + 1, last_error = ?
            WHERE id = ?
            """,
            (error.strip()[:500], clean_id),
        )
        self._connection.commit()
        return self._get_notification_outbox(clean_id)

    def _get_notification_outbox(self, notification_id: str) -> NotificationOutboxRecord:
        row = self._connection.execute(
            """
            SELECT *
            FROM notification_outbox
            WHERE id = ?
            """,
            (notification_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"Notification outbox record not found: {notification_id}")
        return _notification_outbox_from_row(row)

    def _insert_entity(self, entity: Entity) -> None:
        self._connection.execute(
            """
            INSERT INTO entities (
                id, kind, canonical_name, normalized_name, aliases_json,
                first_seen, last_seen, status, tags_json, summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _entity_values(entity),
        )
        self._replace_aliases(entity)
        self._connection.commit()

    def _update_entity(self, entity: Entity) -> None:
        self._connection.execute(
            """
            UPDATE entities
            SET canonical_name = ?,
                normalized_name = ?,
                aliases_json = ?,
                first_seen = ?,
                last_seen = ?,
                status = ?,
                tags_json = ?,
                summary = ?
            WHERE id = ?
            """,
            (
                entity.canonical_name,
                _normalize(entity.canonical_name),
                json.dumps(entity.aliases),
                entity.first_seen,
                entity.last_seen,
                entity.status,
                json.dumps(entity.tags),
                entity.summary,
                entity.id,
            ),
        )
        self._replace_aliases(entity)
        self._connection.commit()

    def _replace_aliases(self, entity: Entity) -> None:
        self._connection.execute("DELETE FROM entity_aliases WHERE entity_id = ?", (entity.id,))
        for alias in entity.aliases:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO entity_aliases (entity_id, kind, alias, normalized_alias)
                VALUES (?, ?, ?, ?)
                """,
                (entity.id, entity.kind, alias, _normalize(alias)),
            )


def _entity_values(entity: Entity) -> tuple[str, str, str, str, str, str, str, str, str, str]:
    return (
        entity.id,
        entity.kind,
        entity.canonical_name,
        _normalize(entity.canonical_name),
        json.dumps(entity.aliases),
        entity.first_seen,
        entity.last_seen,
        entity.status,
        json.dumps(entity.tags),
        entity.summary,
    )


def _entity_from_row(row: sqlite3.Row) -> Entity:
    return Entity(
        id=str(row["id"]),
        kind=str(row["kind"]),
        canonical_name=str(row["canonical_name"]),
        aliases=tuple(json.loads(str(row["aliases_json"]))),
        first_seen=str(row["first_seen"]),
        last_seen=str(row["last_seen"]),
        status=str(row["status"]),
        tags=tuple(json.loads(str(row["tags_json"]))),
        summary=str(row["summary"]),
    )


def _observation_from_row(row: sqlite3.Row) -> Observation:
    return Observation(
        id=str(row["id"]),
        entity_id=str(row["entity_id"]),
        observed_at=str(row["observed_at"]),
        source_type=str(row["source_type"]),
        source_url=str(row["source_url"]),
        metric_name=str(row["metric_name"]),
        previous_value=str(row["previous_value"]),
        current_value=str(row["current_value"]),
        raw_evidence=str(row["raw_evidence"]),
        confidence=str(row["confidence"]),
    )


def _relationship_from_row(row: sqlite3.Row) -> EntityRelationship:
    return EntityRelationship(
        id=str(row["id"]),
        source_entity_id=str(row["source_entity_id"]),
        target_entity_id=str(row["target_entity_id"]),
        relation_type=str(row["relation_type"]),
        evidence=str(row["evidence"]),
        confidence=str(row["confidence"]),
    )


def _decision_from_row(row: sqlite3.Row) -> Decision:
    return Decision(
        id=str(row["id"]),
        signal_id=str(row["signal_id"]),
        action=str(row["action"]),  # type: ignore[arg-type]
        rationale=str(row["rationale"]),
        expected_payoff=str(row["expected_payoff"]),
        risk=str(row["risk"]),
        revisit_date=str(row["revisit_date"]),
        confidence=str(row["confidence"]),
    )


def _brief_from_row(row: sqlite3.Row) -> BriefRecord:
    return BriefRecord(
        id=str(row["id"]),
        brief_type=str(row["brief_type"]),
        domain=str(row["domain"]),
        period_start=str(row["period_start"]),
        period_end=str(row["period_end"]),
        title=str(row["title"]),
        executive_summary=str(row["executive_summary"]),
        top_actions=tuple(json.loads(str(row["top_actions_json"]))),
        notion_status=str(row["notion_status"]),
        notion_url=str(row["notion_url"]),
        telegram_status=str(row["telegram_status"]),
        telegram_detail=str(row["telegram_detail"]),
    )


def _run_from_row(row: sqlite3.Row) -> RunRecord:
    return RunRecord(
        id=str(row["id"]),
        run_date=str(row["run_date"]),
        stage=str(row["stage"]),
        title=str(row["title"]),
        period_start=str(row["period_start"]),
        period_end=str(row["period_end"]),
        status=str(row["status"]),
        notion_status=str(row["notion_status"]),
        notion_url=str(row["notion_url"]),
        telegram_status=str(row["telegram_status"]),
        telegram_detail=str(row["telegram_detail"]),
        created_at=str(row["created_at"]),
    )


def _notification_outbox_from_row(row: sqlite3.Row) -> NotificationOutboxRecord:
    return NotificationOutboxRecord(
        id=str(row["id"]),
        title=str(row["title"]),
        decisions=tuple(json.loads(str(row["decisions_json"]))),
        top_action=str(row["top_action"]),
        notion_url=str(row["notion_url"]),
        status=str(row["status"]),
        attempts=int(row["attempts"]),
        last_error=str(row["last_error"]),
        created_at=str(row["created_at"]),
        sent_at=str(row["sent_at"]),
    )


def _new_id() -> str:
    return str(uuid.uuid4())


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _required(value: str, name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{name} must not be empty.")
    return cleaned


def _optional(value: str, default: str) -> str:
    cleaned = value.strip()
    return cleaned or default


def _normalized_values(values: tuple[str, ...]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for value in values:
        cleaned = value.strip()
        if cleaned:
            normalized.setdefault(cleaned, _normalize(cleaned))
    return normalized


def _normalize(value: str) -> str:
    return " ".join(value.strip().casefold().split())
