from __future__ import annotations

from dataclasses import dataclass

from connectors.github import GitHubRepoSnapshot
from core.memory import Decision, Entity, MemoryStore, Observation


@dataclass(frozen=True)
class RepositoryRadarResult:
    entity: Entity
    observations: tuple[Observation, ...]
    decision: Decision
    star_delta: int
    momentum: str
    signal_title: str
    brief_line: str


def ingest_repository_snapshot(
    store: MemoryStore,
    snapshot: GitHubRepoSnapshot,
    *,
    revisit_date: str,
) -> RepositoryRadarResult:
    entity = store.upsert_entity(
        kind="repository",
        canonical_name=snapshot.full_name,
        observed_at=snapshot.observed_at,
        aliases=(snapshot.name, snapshot.url),
        tags=("github", *snapshot.topics),
        summary=snapshot.description,
    )
    history = store.get_entity_history(entity.id)
    previous_stars = _latest_int_metric(history, "stars", snapshot.stars)
    star_delta = snapshot.stars - previous_stars

    observations = [
        store.record_observation(
            entity_id=entity.id,
            observed_at=snapshot.observed_at,
            source_type="github",
            source_url=snapshot.url,
            metric_name="stars",
            previous_value=previous_stars,
            current_value=snapshot.stars,
            raw_evidence=f"GitHub repository snapshot for {snapshot.full_name}.",
            confidence="high",
        ),
        store.record_observation(
            entity_id=entity.id,
            observed_at=snapshot.observed_at,
            source_type="github",
            source_url=snapshot.url,
            metric_name="open_issues",
            previous_value=_latest_int_metric(history, "open_issues", snapshot.open_issues),
            current_value=snapshot.open_issues,
            raw_evidence=f"GitHub repository snapshot for {snapshot.full_name}.",
            confidence="high",
        ),
    ]

    if snapshot.latest_release:
        observations.append(
            store.record_observation(
                entity_id=entity.id,
                observed_at=snapshot.observed_at,
                source_type="github",
                source_url=snapshot.latest_release_url or snapshot.url,
                metric_name="latest_release",
                previous_value=_latest_text_metric(history, "latest_release", ""),
                current_value=snapshot.latest_release,
                raw_evidence=f"Latest GitHub release for {snapshot.full_name}.",
                confidence="high",
            )
        )
    if snapshot.latest_pull_request:
        observations.append(
            store.record_observation(
                entity_id=entity.id,
                observed_at=snapshot.observed_at,
                source_type="github",
                source_url=snapshot.latest_pull_request_url or snapshot.url,
                metric_name="latest_pull_request",
                previous_value=_latest_text_metric(history, "latest_pull_request", ""),
                current_value=snapshot.latest_pull_request,
                raw_evidence=f"Latest GitHub pull request activity for {snapshot.full_name}.",
                confidence="medium",
            )
        )
    if snapshot.latest_issue:
        observations.append(
            store.record_observation(
                entity_id=entity.id,
                observed_at=snapshot.observed_at,
                source_type="github",
                source_url=snapshot.latest_issue_url or snapshot.url,
                metric_name="latest_issue",
                previous_value=_latest_text_metric(history, "latest_issue", ""),
                current_value=snapshot.latest_issue,
                raw_evidence=f"Latest GitHub issue activity for {snapshot.full_name}.",
                confidence="medium",
            )
        )
    if snapshot.contributor_count:
        observations.append(
            store.record_observation(
                entity_id=entity.id,
                observed_at=snapshot.observed_at,
                source_type="github",
                source_url=snapshot.url,
                metric_name="contributors",
                previous_value=_latest_int_metric(history, "contributors", snapshot.contributor_count),
                current_value=snapshot.contributor_count,
                raw_evidence=f"GitHub contributor page sample for {snapshot.full_name}.",
                confidence="medium",
            )
        )

    for topic in snapshot.topics:
        technology = store.upsert_entity(
            kind="technology",
            canonical_name=topic,
            observed_at=snapshot.observed_at,
            tags=("github-topic",),
            summary=f"Technology topic observed from GitHub repository {snapshot.full_name}.",
        )
        store.link_entities(
            source_entity_id=entity.id,
            target_entity_id=technology.id,
            relation_type="tagged_with",
            evidence=f"GitHub topic on {snapshot.full_name}: {topic}",
            confidence="medium",
        )

    has_activity = bool(snapshot.latest_release or snapshot.latest_pull_request or snapshot.latest_issue)
    momentum = _momentum_label(star_delta, has_activity)
    action = _decision_action(snapshot, star_delta, has_activity, history)
    signal_title = f"{snapshot.full_name} momentum: {momentum}"
    decision = store.record_decision(
        signal_id=f"github-repo:{snapshot.full_name}:{snapshot.observed_at}",
        action=action,
        rationale=_decision_rationale(snapshot, star_delta, momentum, action, history),
        expected_payoff=_expected_payoff(action),
        risk="GitHub activity can reflect hype, automation, or short-lived attention rather than durable engineering value.",
        revisit_date=revisit_date,
        confidence="medium" if star_delta or snapshot.latest_release else "low",
    )

    brief_line = (
        f"{decision.action}: {snapshot.full_name} has {snapshot.stars} stars "
        f"({star_delta:+d} since last observation), momentum {momentum}. "
        f"下一步：{_brief_next_step(snapshot, star_delta, decision.action)}"
    )
    return RepositoryRadarResult(
        entity=entity,
        observations=tuple(observations),
        decision=decision,
        star_delta=star_delta,
        momentum=momentum,
        signal_title=signal_title,
        brief_line=brief_line,
    )


def _latest_int_metric(history: list[Observation], metric_name: str, fallback: int) -> int:
    for observation in reversed(history):
        if observation.metric_name == metric_name:
            try:
                return int(observation.current_value)
            except ValueError:
                return fallback
    return fallback


def _latest_text_metric(history: list[Observation], metric_name: str, fallback: str) -> str:
    for observation in reversed(history):
        if observation.metric_name == metric_name:
            return observation.current_value
    return fallback


def _momentum_label(star_delta: int, has_activity: bool) -> str:
    if star_delta >= 1000 and has_activity:
        return "surging"
    if star_delta >= 500:
        return "rising"
    if has_activity or star_delta >= 100:
        return "active"
    if star_delta > 0:
        return "watch"
    return "flat"


def _decision_action(
    snapshot: GitHubRepoSnapshot,
    star_delta: int,
    has_activity: bool,
    history: list[Observation],
):
    score = 0
    if snapshot.latest_release:
        score += 22
        if _is_major_release(snapshot.latest_release):
            score += 10
    if star_delta >= 500:
        score += 25
    elif star_delta >= 100:
        score += 10
    elif star_delta > 0:
        score += 4
    if has_activity:
        score += 15
    contributor_delta = _metric_delta(history, "contributors", snapshot.contributor_count)
    if contributor_delta >= 10:
        score += 10
    elif contributor_delta > 0:
        score += 5
    if _is_new_entity(history) and not snapshot.latest_release:
        score += 5
    if _previous_star_delta(history) is not None and star_delta > max(_previous_star_delta(history) or 0, 1) * 2:
        score += 10
    if any(topic in _interest_topics() for topic in snapshot.topics):
        score += 5

    if score >= 50:
        return "Prototype"
    if score >= 30:
        return "Read"
    if score >= 15:
        return "Watch"
    return "Ignore"


def _decision_rationale(
    snapshot: GitHubRepoSnapshot,
    star_delta: int,
    momentum: str,
    action: str,
    history: list[Observation],
) -> str:
    parts = []
    if snapshot.latest_release:
        parts.append(
            f"Why now: 剛發布 {snapshot.latest_release}，值得關注新版本帶來的能力變化"
            f"{_date_suffix(snapshot.latest_release_published_at)}。"
        )
    elif star_delta >= 500:
        parts.append(f"Why now: stars 較前次觀察增加 {star_delta:+d}，社群注意力正在升高。")
    elif has_engineering_activity(snapshot):
        parts.append("Why now: 雖然 star 變化不大，但 release、PR 或 issue 活動提供工程進展佐證。")
    else:
        parts.append(f"Why now: {snapshot.full_name} 目前是 {momentum} 訊號，缺少新的工程事件。")

    previous_delta = _previous_star_delta(history)
    if previous_delta is not None:
        if star_delta > max(previous_delta, 1) * 2:
            parts.append(f"What changed: 增速較前次觀察明顯加快（前次 {previous_delta:+d}），加速趨勢成立。")
        elif previous_delta > 0 and star_delta < previous_delta / 2:
            parts.append(f"What changed: 增速低於前次一半（前次 {previous_delta:+d}），熱度需要重新驗證。")
        else:
            parts.append(f"What changed: 相較前次 star delta {previous_delta:+d}，本次變化屬於延續性訊號。")
    elif _is_new_entity(history):
        parts.append("What changed: 這是首次進入 radar 的觀察，先建立 baseline，後續用 star/release delta 判斷趨勢。")

    if snapshot.topics:
        parts.append(f"Connects to: {', '.join(snapshot.topics[:4])}。")
    else:
        parts.append("Connects to: 目前沒有 GitHub topic 可用於 radar 關聯。")

    activity = []
    if snapshot.latest_pull_request:
        activity.append(f"PR: {snapshot.latest_pull_request}")
    if snapshot.latest_issue:
        activity.append(f"issue: {snapshot.latest_issue}")
    if activity:
        parts.append("近期工程脈絡包括 " + "；".join(activity) + "。")
    contributor_delta = _metric_delta(history, "contributors", snapshot.contributor_count)
    if snapshot.contributor_count:
        if contributor_delta > 0:
            parts.append(f"contributors sample 增加 {contributor_delta:+d} 至 {snapshot.contributor_count}，維護面正在擴張。")
        else:
            parts.append(f"contributors sample 為 {snapshot.contributor_count}，可作為維護面廣度的粗略參考。")
    parts.append("What to do: " + _action_guidance(action, "repo"))
    parts.append(_confidence_text(snapshot, star_delta, history))
    return " ".join(parts)


def has_engineering_activity(snapshot: GitHubRepoSnapshot) -> bool:
    return bool(snapshot.latest_release or snapshot.latest_pull_request or snapshot.latest_issue)


def _previous_star_delta(history: list[Observation]) -> int | None:
    for observation in reversed(history):
        if observation.metric_name == "stars":
            try:
                return int(observation.current_value) - int(observation.previous_value)
            except ValueError:
                return None
    return None


def _metric_delta(history: list[Observation], metric_name: str, current_value: int) -> int:
    previous = _latest_int_metric(history, metric_name, current_value)
    return current_value - previous


def _is_new_entity(history: list[Observation]) -> bool:
    return not history


def _interest_topics() -> set[str]:
    return {
        "agent",
        "agents",
        "ai-agent",
        "developer-tools",
        "rag",
        "inference",
        "quantization",
        "multimodal",
        "tool-use",
        "coding-agent",
    }


def _action_guidance(action: str, subject: str) -> str:
    if action == "Prototype":
        return f"建議行動：Prototype，抽取這個 {subject} 的架構或 workflow 做小實驗。"
    if action == "Read":
        return f"建議行動：Read，先讀 release/issue/README 判斷是否值得 prototype。"
    if action == "Watch":
        return f"建議行動：Watch，保持在 radar 中等待更強工程證據。"
    return "建議行動：Ignore，暫時不要投入注意力。"


def _brief_next_step(snapshot: GitHubRepoSnapshot, star_delta: int, action: str) -> str:
    if star_delta == 0 and action in {"Read", "Watch", "Ignore"}:
        return "只建立 baseline，等下一次 star/release delta 再升級。"
    if action == "Prototype":
        return "抽一個 workflow 或架構做最小實驗。"
    if action == "Read":
        return "讀 release notes、近期 PR 和 README 判斷是否值得 prototype。"
    if action == "Watch":
        return "保留在 radar，等待更強工程事件。"
    return "暫時不投入每日注意力。"


def _confidence_text(snapshot: GitHubRepoSnapshot, star_delta: int, history: list[Observation]) -> str:
    if snapshot.latest_release and (star_delta >= 100 or has_engineering_activity(snapshot)):
        return "Confidence: 中高 — release 與活躍度同時支持判斷。"
    if has_engineering_activity(snapshot):
        return "Confidence: 中 — 有工程活動，但仍需後續觀察確認是否持續。"
    if history and star_delta < 100:
        return "Confidence: 低 — 缺乏 release/PR/issue 佐證。"
    return "Confidence: 中 — 已建立 baseline，後續以趨勢變化校準。"


def _date_suffix(value: str) -> str:
    if not value:
        return ""
    return f"（{value[:10]}）"


def _is_major_release(value: str) -> bool:
    cleaned = value.strip().lower().lstrip("v")
    parts = cleaned.split(".")
    if len(parts) < 2:
        return False
    return len(parts) >= 3 and parts[1] == "0" and parts[2].split("-", 1)[0] == "0"


def _expected_payoff(action: str) -> str:
    if action == "Prototype":
        return "Validate whether the repository contains implementation patterns Hermes should adopt or track closely."
    if action == "Read":
        return "Understand the repository direction before deciding whether to prototype."
    if action == "Watch":
        return "Keep the entity in radar memory until stronger evidence appears."
    return "Avoid spending attention until momentum or engineering evidence improves."
