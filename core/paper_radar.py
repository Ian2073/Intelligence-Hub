from __future__ import annotations

from dataclasses import dataclass

from connectors.papers import PaperSnapshot
from core.memory import Decision, Entity, EntityRelationship, MemoryStore, Observation


@dataclass(frozen=True)
class PaperRadarResult:
    entity: Entity
    observations: tuple[Observation, ...]
    relationships: tuple[EntityRelationship, ...]
    decision: Decision
    signal_title: str
    brief_line: str


def ingest_paper_snapshot(
    store: MemoryStore,
    snapshot: PaperSnapshot,
    *,
    revisit_date: str,
) -> PaperRadarResult:
    entity = store.upsert_entity(
        kind="paper",
        canonical_name=snapshot.title,
        observed_at=snapshot.observed_at,
        aliases=(snapshot.url,),
        tags=("paper", *snapshot.categories, *snapshot.technologies),
        summary=snapshot.abstract,
    )
    observations = (
        store.record_observation(
            entity_id=entity.id,
            observed_at=snapshot.observed_at,
            source_type="paper",
            source_url=snapshot.url,
            metric_name="published",
            previous_value="",
            current_value=snapshot.published_at,
            raw_evidence=f"Paper metadata observed for {snapshot.title}.",
            confidence="medium",
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
                relation_type="uses_or_advances",
                observed_at=snapshot.observed_at,
                evidence=f"Paper explicitly maps to technology: {technology}.",
            )
        )
    for repository in snapshot.repositories:
        relationships.append(
            _link_named_entity(
                store,
                source=entity,
                target_kind="repository",
                target_name=repository,
                relation_type="related_repository",
                observed_at=snapshot.observed_at,
                evidence=f"Paper references related repository: {repository}.",
            )
        )
    for company in snapshot.companies:
        relationships.append(
            _link_named_entity(
                store,
                source=entity,
                target_kind="company",
                target_name=company,
                relation_type="related_company",
                observed_at=snapshot.observed_at,
                evidence=f"Paper references related company: {company}.",
            )
        )

    action = _decision_action(snapshot)
    decision = store.record_decision(
        signal_id=f"paper:{snapshot.title}:{snapshot.observed_at}",
        action=action,
        rationale=_decision_rationale(snapshot),
        expected_payoff=_expected_payoff(action),
        risk="Paper impact may be overstated until code, replication, or adoption evidence appears.",
        revisit_date=revisit_date,
        confidence="medium" if relationships else "low",
    )
    brief_line = (
        f"{decision.action}: {snapshot.title} connects to {len(relationships)} radar entities. "
        f"下一步：檢查 {snapshot.repositories[0] if snapshot.repositories else 'paper method'} 是否能做最小驗證。"
    )
    return PaperRadarResult(
        entity=entity,
        observations=observations,
        relationships=tuple(relationships),
        decision=decision,
        signal_title=f"Paper radar: {snapshot.title}",
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
        summary=f"{target_kind.title()} observed through paper radar.",
    )
    return store.link_entities(
        source_entity_id=source.id,
        target_entity_id=target.id,
        relation_type=relation_type,
        evidence=evidence,
        confidence="medium",
    )


def _decision_action(snapshot: PaperSnapshot):
    score = 0
    text = f"{snapshot.title} {snapshot.abstract}".casefold()
    if snapshot.repositories:
        score += 30
    if snapshot.technologies:
        score += min(20, len(snapshot.technologies) * 8)
    if snapshot.companies:
        score += 10
    if any(keyword in text for keyword in ("new method", "new architecture", "framework", "algorithm", "system", "agentic")):
        score += 18
    if any(keyword in text for keyword in ("benchmark", "evaluation", "dataset", "suite")):
        score += 10
    if any(keyword in text for keyword in ("survey", "position paper", "taxonomy", "overview")):
        score -= 8
    if any(keyword in text for keyword in ("code", "implementation", "open source", "github")):
        score += 12

    if score >= 55:
        return "Prototype"
    if score >= 32:
        return "Read"
    if score >= 12:
        return "Watch"
    return "Review later"


def _decision_rationale(snapshot: PaperSnapshot) -> str:
    connected = len(snapshot.technologies) + len(snapshot.repositories) + len(snapshot.companies)
    action = _decision_action(snapshot)
    parts = [f"Why now: 這篇論文把研究主題連到 {connected} 個 radar 實體。"]
    parts.append(f"What changed: 新觀察到的研究問題是 {_trim(snapshot.abstract)}。")
    if snapshot.technologies:
        parts.append(f"Connects to: {', '.join(snapshot.technologies[:4])}。")
    if snapshot.repositories:
        parts.append(f"Implementation signal: repo {', '.join(snapshot.repositories[:3])} 可直接檢查是否已有可復現或可借鑑的實作。")
    elif snapshot.companies:
        parts.append(f"Implementation signal: company {', '.join(snapshot.companies[:3])} 適合判斷生態或產品方向。")
    else:
        parts.append("Implementation signal: 目前沒有 repo/company 佐證，需避免把純研究新穎性誤判成可立即落地。")
    parts.append("What to do: " + _paper_action_guidance(action))
    parts.append(_paper_confidence(snapshot))
    return " ".join(parts)


def _paper_action_guidance(action: str) -> str:
    if action == "Prototype":
        return "建議行動：Prototype，先找 repo、方法細節或可替代實作做最小驗證。"
    if action == "Read":
        return "建議行動：Read，判斷它是否改變現有 radar 實體的技術路線。"
    if action == "Watch":
        return "建議行動：Watch，等待 repo、引用或公司採用訊號補強。"
    return "建議行動：Review later，暫時只保留 metadata。"


def _paper_confidence(snapshot: PaperSnapshot) -> str:
    if snapshot.repositories and snapshot.technologies:
        return "Confidence: 中高 — 論文同時具備技術與實作關聯。"
    if snapshot.technologies or snapshot.companies:
        return "Confidence: 中 — 有明確 radar 關聯，但落地性仍需驗證。"
    return "Confidence: 低 — 目前缺少可交叉驗證的外部關聯。"


def _trim(text: str, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _expected_payoff(action: str) -> str:
    if action == "Prototype":
        return "Test whether the paper has implementation value beyond the abstract."
    if action == "Read":
        return "Understand the paper's ecosystem implication before deeper work."
    if action == "Watch":
        return "Track whether related repositories or companies appear later."
    return "Revisit only if stronger related evidence appears."
