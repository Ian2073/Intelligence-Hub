from __future__ import annotations

from dataclasses import dataclass


ACTION_RANK: dict[str, int] = {
    "Implement": 0,
    "Prototype": 1,
    "Read": 2,
    "Watch": 3,
    "Review later": 4,
    "Ignore": 5,
}


@dataclass(frozen=True)
class QualityIssue:
    code: str
    detail: str


def action_name(line: str) -> str:
    return line.split(":", 1)[0].strip() or "Watch"


def compact_action(line: str, *, max_chars: int = 180) -> str:
    action = action_name(line)
    body = line.split(":", 1)[1].strip() if ":" in line else line.strip()
    for marker in (" 下一步：", " What to do:", " 建議行動："):
        if marker in body:
            body = body.split(marker, 1)[0].strip()
    body = _strip_rationale_labels(body)
    body = _strip_metric_parenthetical(body)
    body = _localize_action_body(body)
    body = " ".join(body.split())
    compact = f"{action}: {body}" if body else action
    return trim_text(compact, max_chars)


def unique_actions(actions: tuple[str, ...] | list[str], *, limit: int = 7, max_chars: int = 180) -> tuple[str, ...]:
    ranked = sorted((compact_action(action, max_chars=max_chars) for action in actions), key=_action_sort_key)
    selected: list[str] = []
    seen: set[str] = set()
    for action in ranked:
        identity = _identity(action)
        if identity in seen:
            continue
        selected.append(action)
        seen.add(identity)
        if len(selected) >= limit:
            break
    return tuple(selected)


def build_executive_judgment(
    *,
    period_label: str,
    top_actions: tuple[str, ...],
    trends: tuple[tuple[str, str, str], ...] = (),
    decision_review_count: int = 0,
) -> str:
    if not top_actions and not trends and decision_review_count == 0:
        return f"{period_label} 沒有需要升級的訊號；維持觀察，避免為低價值雜訊分心。"

    priority = compact_action(top_actions[0], max_chars=120) if top_actions else "Watch: 暫無高優先級行動"
    up_trends = [name for name, direction, _ in trends if direction == "Up"]
    review_text = f"；另有 {decision_review_count} 個舊決策需要回看" if decision_review_count else ""
    trend_text = f"主要升溫方向是 {', '.join(up_trends[:3])}" if up_trends else "沒有明確升溫主題"
    return (
        f"{_judgment_label(period_label)}{trend_text}{review_text}。"
        f"最高優先行動是 {priority}。"
        " 其餘訊號只保留在 radar，除非後續出現 release、採用或跨來源佐證。"
    )


def validate_brief_quality(
    *,
    executive_summary: str,
    top_actions: tuple[str, ...],
    max_actions: int = 7,
) -> tuple[QualityIssue, ...]:
    issues: list[QualityIssue] = []
    if len(top_actions) > max_actions:
        issues.append(QualityIssue("too_many_actions", f"{len(top_actions)} actions exceeds {max_actions}."))
    if len(set(_identity(action) for action in top_actions)) != len(top_actions):
        issues.append(QualityIssue("duplicate_actions", "Top actions contain duplicate identities."))
    if "Hermes used" in executive_summary or "observations from memory" in executive_summary:
        issues.append(QualityIssue("system_metric_summary", "Executive summary leads with system metrics instead of judgment."))
    if top_actions and not any(executive_summary.startswith(prefix) or prefix in executive_summary for prefix in ("判斷", "最高優先", "升溫", "行動")):
        issues.append(QualityIssue("weak_judgment", "Executive summary does not clearly surface judgment or action."))
    return tuple(issues)


def trim_text(text: str, max_chars: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip(" ,，;；") + "…"


def _judgment_label(period_label: str) -> str:
    separator = " " if period_label and period_label[-1].isascii() else ""
    return f"{period_label}{separator}的判斷是："


def _action_sort_key(line: str) -> tuple[int, str]:
    return (ACTION_RANK.get(action_name(line), 9), line.casefold())


def _identity(line: str) -> str:
    action = action_name(line).casefold()
    body = line.split(":", 1)[1] if ":" in line else line
    for separator in (" connects to ", " has ", "(", "。", "，", " - "):
        if separator in body:
            body = body.split(separator, 1)[0]
    return f"{action}:{body.strip().casefold()}"


def _strip_rationale_labels(text: str) -> str:
    for label in ("Why now:", "What changed:", "Connects to:", "What to do:", "Confidence:"):
        text = text.replace(label, "")
    return text.strip()


def _strip_metric_parenthetical(text: str) -> str:
    markers = (" (impact ", " (score ")
    for marker in markers:
        if marker in text:
            return text.split(marker, 1)[0].rstrip(" .。")
    return text


def _localize_action_body(text: str) -> str:
    if " connects to " in text and " radar entities" in text:
        subject, rest = text.split(" connects to ", 1)
        count = rest.split(" radar entities", 1)[0].strip()
        return f"{subject} 連到 {count} 個 radar 實體"
    if " has " in text and " stars " in text:
        subject, rest = text.split(" has ", 1)
        stars = rest.split(" stars", 1)[0].strip()
        return f"{subject} 目前 {stars} stars"
    return text
