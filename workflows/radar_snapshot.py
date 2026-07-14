from __future__ import annotations

from dataclasses import dataclass

from core.decision_engine import ACTION_RANK
from core.memory import Decision, Entity, MemoryStore
from core.report_quality import unique_actions


@dataclass(frozen=True)
class RadarEntry:
    kind: str
    name: str
    status: str
    last_seen: str
    summary: str
    tags: tuple[str, ...]
    observation_count: int
    relationship_count: int
    recent_metrics: tuple[str, ...]


@dataclass(frozen=True)
class RadarSnapshot:
    title: str
    executive_summary: str
    entries: tuple[RadarEntry, ...]
    top_actions: tuple[str, ...]
    decisions: tuple[Decision, ...]


def build_radar_snapshot(
    store: MemoryStore,
    *,
    as_of: str,
    since: str | None = None,
    max_entries: int = 25,
) -> RadarSnapshot:
    entities = store.list_entities()
    observations = store.list_observations(since=since, until=as_of)
    relationships = store.list_relationships()
    decisions = store.list_decisions(since=since)
    ranked_decisions = _rank_unique_decisions(decisions, limit=7)
    entries = tuple(
        sorted(
            (_entry(entity, observations, relationships) for entity in entities),
            key=lambda item: (item.observation_count + item.relationship_count, item.last_seen),
            reverse=True,
        )[:max_entries]
    )
    top_actions = unique_actions(tuple(_decision_action_line(decision) for decision in ranked_decisions), limit=7)
    kind_counts = _kind_counts(entries)
    summary = (
        f"Radar 判斷：目前有 {len(entries)} 個活躍實體，"
        f"主力集中在 {', '.join(f'{kind}={count}' for kind, count in kind_counts.items()) or '尚無分類'}。"
        f"最近 {len(observations)} 筆 observation 和 {len(relationships)} 條 relationship 顯示，"
        f"最高優先行動是 {top_actions[0] if top_actions else 'Watch: 維持觀察'}。"
    )
    return RadarSnapshot(
        title=f"Intelligence Hub Radar Snapshot - {as_of}",
        executive_summary=summary,
        entries=entries,
        top_actions=top_actions,
        decisions=ranked_decisions,
    )


def _entry(entity: Entity, observations, relationships) -> RadarEntry:
    entity_observations = [observation for observation in observations if observation.entity_id == entity.id]
    entity_relationships = [
        relationship
        for relationship in relationships
        if relationship.source_entity_id == entity.id or relationship.target_entity_id == entity.id
    ]
    recent_metrics = tuple(
        f"{observation.metric_name}: {observation.previous_value} -> {observation.current_value}"
        for observation in entity_observations[-3:]
    )
    return RadarEntry(
        kind=entity.kind,
        name=entity.canonical_name,
        status=entity.status,
        last_seen=entity.last_seen,
        summary=entity.summary,
        tags=entity.tags,
        observation_count=len(entity_observations),
        relationship_count=len(entity_relationships),
        recent_metrics=recent_metrics,
    )


def _kind_counts(entries: tuple[RadarEntry, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.kind] = counts.get(entry.kind, 0) + 1
    return counts


def _action_rank(action: str) -> int:
    return ACTION_RANK.get(action, 9)


def _rank_unique_decisions(decisions: list[Decision], *, limit: int) -> tuple[Decision, ...]:
    selected: list[Decision] = []
    seen: set[str] = set()
    for decision in sorted(decisions, key=lambda item: (_action_rank(item.action), item.signal_id.casefold(), item.id)):
        identity = decision.signal_id.rsplit(":", 1)[0].casefold()
        if identity in seen:
            continue
        selected.append(decision)
        seen.add(identity)
        if len(selected) >= limit:
            break
    return tuple(selected)


def _decision_action_line(decision: Decision) -> str:
    subject = decision.signal_id.rsplit(":", 1)[0].replace("github-repo:", "").replace("paper:", "").replace("domain:", "")
    subject = subject.replace(":", ": ", 1)
    return f"{decision.action}: {subject} - {_first_clause(decision.rationale)}"


def _first_clause(text: str) -> str:
    cleaned = " ".join(text.split())
    for separator in ("。", ". "):
        if separator in cleaned:
            return cleaned.split(separator, 1)[0].strip()
    return cleaned
