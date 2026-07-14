from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from core.memory import MemoryStore


@dataclass(frozen=True)
class MemoryExportResult:
    output_dir: Path
    entities_path: Path
    observations_path: Path
    relationships_path: Path
    decisions_path: Path
    briefs_path: Path
    runs_path: Path
    notification_outbox_path: Path
    index_path: Path
    entity_count: int
    observation_count: int
    relationship_count: int
    decision_count: int
    brief_count: int
    run_count: int
    notification_outbox_count: int


def export_memory(store: MemoryStore, *, output_dir: Path, as_of: str) -> MemoryExportResult:
    resolved = output_dir.resolve()
    resolved.mkdir(parents=True, exist_ok=True)

    entities = store.list_entities()
    observations = store.list_observations()
    relationships = store.list_relationships()
    decisions = store.list_decisions()
    briefs = store.list_briefs()
    runs = store.list_runs()
    notification_outbox = store.list_notification_outbox()

    entities_path = resolved / "entities.jsonl"
    observations_path = resolved / "observations.jsonl"
    relationships_path = resolved / "relationships.jsonl"
    decisions_path = resolved / "decisions.jsonl"
    briefs_path = resolved / "briefs.jsonl"
    runs_path = resolved / "runs.jsonl"
    notification_outbox_path = resolved / "notification_outbox.jsonl"
    index_path = resolved / "README.md"

    _write_jsonl(entities_path, entities)
    _write_jsonl(observations_path, observations)
    _write_jsonl(relationships_path, relationships)
    _write_jsonl(decisions_path, decisions)
    _write_jsonl(briefs_path, briefs)
    _write_jsonl(runs_path, runs)
    _write_jsonl(notification_outbox_path, notification_outbox)
    index_path.write_text(
        _index_markdown(
            as_of=as_of,
            entity_count=len(entities),
            observation_count=len(observations),
            relationship_count=len(relationships),
            decision_count=len(decisions),
            brief_count=len(briefs),
            run_count=len(runs),
            notification_outbox_count=len(notification_outbox),
        ),
        encoding="utf-8",
    )

    return MemoryExportResult(
        output_dir=resolved,
        entities_path=entities_path,
        observations_path=observations_path,
        relationships_path=relationships_path,
        decisions_path=decisions_path,
        briefs_path=briefs_path,
        runs_path=runs_path,
        notification_outbox_path=notification_outbox_path,
        index_path=index_path,
        entity_count=len(entities),
        observation_count=len(observations),
        relationship_count=len(relationships),
        decision_count=len(decisions),
        brief_count=len(briefs),
        run_count=len(runs),
        notification_outbox_count=len(notification_outbox),
    )


def _write_jsonl(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def _index_markdown(
    *,
    as_of: str,
    entity_count: int,
    observation_count: int,
    relationship_count: int,
    decision_count: int,
    brief_count: int,
    run_count: int,
    notification_outbox_count: int,
) -> str:
    return "\n".join(
        [
            "# Hermes Memory Export",
            "",
            f"As of: {as_of}",
            "",
            "| File | Rows |",
            "| --- | ---: |",
            f"| entities.jsonl | {entity_count} |",
            f"| observations.jsonl | {observation_count} |",
            f"| relationships.jsonl | {relationship_count} |",
            f"| decisions.jsonl | {decision_count} |",
            f"| briefs.jsonl | {brief_count} |",
            f"| runs.jsonl | {run_count} |",
            f"| notification_outbox.jsonl | {notification_outbox_count} |",
            "",
            "This export is read-only evidence of Hermes runtime memory. SQLite remains the runtime store.",
            "",
        ]
    )
