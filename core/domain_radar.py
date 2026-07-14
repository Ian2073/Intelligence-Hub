from __future__ import annotations

from dataclasses import dataclass

from connectors.domain import DomainSignalSnapshot
from core.memory import Decision, Entity, EntityRelationship, MemoryStore, Observation


@dataclass(frozen=True)
class DomainRadarResult:
    entity: Entity
    observations: tuple[Observation, ...]
    relationships: tuple[EntityRelationship, ...]
    decision: Decision
    priority_score: int
    signal_title: str
    brief_line: str


def ingest_domain_signal_snapshot(
    store: MemoryStore,
    snapshot: DomainSignalSnapshot,
    *,
    revisit_date: str,
) -> DomainRadarResult:
    entity = store.upsert_entity(
        kind=snapshot.entity_kind,
        canonical_name=snapshot.entity_name,
        observed_at=snapshot.observed_at,
        aliases=(snapshot.title, snapshot.source_url),
        tags=(snapshot.domain, *snapshot.tags),
        summary=snapshot.summary,
    )
    history = store.get_entity_history(entity.id)
    previous_score = _latest_int_metric(history, "impact_score", snapshot.impact_score)
    score_delta = snapshot.impact_score - previous_score
    observations = (
        store.record_observation(
            entity_id=entity.id,
            observed_at=snapshot.observed_at,
            source_type=f"domain:{snapshot.domain}",
            source_url=snapshot.source_url,
            metric_name="impact_score",
            previous_value=previous_score,
            current_value=snapshot.impact_score,
            raw_evidence=snapshot.evidence,
            confidence=snapshot.confidence,
        ),
        store.record_observation(
            entity_id=entity.id,
            observed_at=snapshot.observed_at,
            source_type=f"domain:{snapshot.domain}",
            source_url=snapshot.source_url,
            metric_name="published",
            previous_value="",
            current_value=snapshot.published_at,
            raw_evidence=snapshot.title,
            confidence=snapshot.confidence,
        ),
    )
    relationships = []
    for technology in snapshot.technologies:
        relationships.append(
            _link_named_entity(
                store,
                source=entity,
                target_kind="technology",
                target_name=technology,
                relation_type="domain_related_technology",
                observed_at=snapshot.observed_at,
                evidence=f"{snapshot.domain} signal links {snapshot.entity_name} to {technology}.",
            )
        )
    for company in snapshot.companies:
        relationships.append(
            _link_named_entity(
                store,
                source=entity,
                target_kind="company",
                target_name=company,
                relation_type="domain_related_company",
                observed_at=snapshot.observed_at,
                evidence=f"{snapshot.domain} signal links {snapshot.entity_name} to {company}.",
            )
        )
    for repository in snapshot.repositories:
        relationships.append(
            _link_named_entity(
                store,
                source=entity,
                target_kind="repository",
                target_name=repository,
                relation_type="domain_related_repository",
                observed_at=snapshot.observed_at,
                evidence=f"{snapshot.domain} signal links {snapshot.entity_name} to {repository}.",
            )
        )

    action = _decision_action(snapshot, score_delta, len(relationships), history)
    decision = store.record_decision(
        signal_id=f"domain:{snapshot.domain}:{snapshot.entity_name}:{snapshot.observed_at}",
        action=action,
        rationale=_decision_rationale(snapshot, score_delta, len(relationships), action, history),
        expected_payoff=_expected_payoff(action),
        risk="Domain signals can be early, noisy, or strategically important without immediate implementation value.",
        revisit_date=revisit_date,
        confidence=snapshot.confidence,
    )
    brief_line = (
        f"{decision.action}: [{snapshot.domain}] {snapshot.title} "
        f"(impact {snapshot.impact_score}, {score_delta:+d} since last observation). "
        f"下一步：判斷 {snapshot.entity_name} 是否影響 radar 路線。"
    )
    return DomainRadarResult(
        entity=entity,
        observations=observations,
        relationships=tuple(relationships),
        decision=decision,
        priority_score=snapshot.impact_score + max(score_delta, 0),
        signal_title=f"{snapshot.domain}: {snapshot.title}",
        brief_line=brief_line,
    )


def _link_named_entity(
    store: MemoryStore,
    *,
    source: Entity,
    target_kind: str,
    target_name: str,
    relation_type: str,
    observed_at: str,
    evidence: str,
) -> EntityRelationship:
    target = store.upsert_entity(
        kind=target_kind,
        canonical_name=target_name,
        observed_at=observed_at,
        summary=f"{target_kind.title()} observed through domain intelligence.",
    )
    return store.link_entities(
        source_entity_id=source.id,
        target_entity_id=target.id,
        relation_type=relation_type,
        evidence=evidence,
        confidence="medium",
    )


def _latest_int_metric(history: list[Observation], metric_name: str, fallback: int) -> int:
    for observation in reversed(history):
        if observation.metric_name == metric_name:
            try:
                return int(observation.current_value)
            except ValueError:
                return fallback
    return fallback


def _decision_action(
    snapshot: DomainSignalSnapshot,
    score_delta: int,
    relationship_count: int,
    history: list[Observation],
):
    if snapshot.recommended_action in {"Ignore", "Watch", "Read", "Prototype", "Implement", "Review later"}:
        return snapshot.recommended_action

    score = _impact_score(snapshot, score_delta, relationship_count, history)

    if score >= 65:
        return "Prototype"
    if score >= 45:
        return "Read"
    if score >= 25:
        return "Watch"
    return "Ignore"


def _impact_score(
    snapshot: DomainSignalSnapshot,
    score_delta: int,
    relationship_count: int,
    history: list[Observation],
) -> int:
    velocity = 100 if score_delta >= 20 else 75 if score_delta >= 10 else 55 if score_delta > 0 else 35
    cross_signal = min(100, relationship_count * 25)
    strategic_relevance = snapshot.impact_score
    prior_count = _prior_signal_count(history)
    novelty = 85 if prior_count == 0 else 55 if prior_count == 1 else 30
    return round(
        velocity * 0.30
        + cross_signal * 0.25
        + strategic_relevance * 0.25
        + novelty * 0.20
    )


def _decision_rationale(
    snapshot: DomainSignalSnapshot,
    score_delta: int,
    relationship_count: int,
    action: str,
    history: list[Observation],
) -> str:
    direction = "升溫" if score_delta > 0 else "降溫" if score_delta < 0 else "持平"
    parts = [
        f"Why now: {snapshot.domain} impact {snapshot.impact_score}/100，較前次觀察{direction} {score_delta:+d}。",
        f"What changed: 摘要指出 {_trim(snapshot.summary)}。",
    ]
    if snapshot.evidence:
        parts.append(f"Evidence: {_trim(snapshot.evidence)}。")
    prior_count = _prior_signal_count(history)
    if prior_count:
        parts.append(f"Memory: 同一 entity 先前已有 {prior_count} 次 domain observation，這不是孤立事件。")
    else:
        parts.append("Memory: 這是該 entity 的首次 domain observation，需先建立趨勢 baseline。")
    if relationship_count:
        linked = [*snapshot.technologies, *snapshot.repositories, *snapshot.companies]
        if linked:
            parts.append(f"Connects to: {', '.join(linked[:5])}。")
        else:
            parts.append(f"Connects to: 已連到 {relationship_count} 個 explicit radar relationship。")
    else:
        parts.append("Connects to: 目前沒有 explicit radar relationship。")
    parts.append("What to do: " + _domain_action_guidance(action))
    parts.append(_domain_confidence(snapshot, score_delta, relationship_count, prior_count))
    return " ".join(parts)


def _prior_signal_count(history: list[Observation]) -> int:
    return sum(1 for observation in history if observation.metric_name == "impact_score")


def _domain_action_guidance(action: str) -> str:
    if action == "Prototype":
        return "建議行動：Prototype，把這個趨勢轉成小型技術驗證或決策 review。"
    if action == "Read":
        return "建議行動：Read，先閱讀來源並判斷是否影響架構、投資注意力或能力路線。"
    if action == "Watch":
        return "建議行動：Watch，等待更多來源或跨訊號佐證。"
    return "建議行動：Ignore，暫時不要讓它佔用每日注意力。"


def _domain_confidence(snapshot: DomainSignalSnapshot, score_delta: int, relationship_count: int, prior_count: int) -> str:
    if snapshot.confidence == "high" and (relationship_count >= 2 or prior_count >= 2):
        return "Confidence: 高 — 來源信心、趨勢記憶與 radar 關聯互相支持。"
    if relationship_count or score_delta > 0:
        return "Confidence: 中 — 有趨勢或關聯佐證，但仍需後續來源確認。"
    return "Confidence: 低 — 目前主要依賴單一 domain 訊號。"


def _trim(text: str, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _expected_payoff(action: str) -> str:
    if action == "Prototype":
        return "Turn the signal into a small experiment before it becomes crowded or strategically obvious."
    if action == "Read":
        return "Spend focused reading time to decide whether this affects architecture, market, or career direction."
    if action == "Watch":
        return "Keep the entity in radar memory and wait for stronger corroborating evidence."
    return "Preserve attention for stronger signals."
