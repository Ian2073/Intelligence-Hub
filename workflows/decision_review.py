from __future__ import annotations

from dataclasses import dataclass

from core.decision_engine import ACTION_RANK
from core.memory import Decision, MemoryStore
from core.report_quality import trim_text, unique_actions


@dataclass(frozen=True)
class DecisionReviewItem:
    decision_id: str
    signal_id: str
    original_action: str
    review_status: str
    rationale: str
    expected_payoff: str
    risk: str
    revisit_date: str
    confidence: str
    recommended_action: str


@dataclass(frozen=True)
class DecisionReviewReport:
    title: str
    executive_summary: str
    items: tuple[DecisionReviewItem, ...]
    top_actions: tuple[str, ...]


def build_decision_review_report(
    store: MemoryStore,
    *,
    as_of: str,
    since: str | None = None,
    limit: int = 10,
) -> DecisionReviewReport:
    decisions = store.list_decisions(since=since, until=as_of)
    ranked = sorted(decisions, key=_decision_sort_key)[:limit]
    items = tuple(_review_item(decision, as_of) for decision in ranked)
    top_actions = unique_actions(tuple(item.recommended_action for item in items), limit=7)
    return DecisionReviewReport(
        title=f"Hermes Decision Review - {as_of}",
        executive_summary=_summary(items, as_of),
        items=items,
        top_actions=top_actions,
    )


def _review_item(decision: Decision, as_of: str) -> DecisionReviewItem:
    status = "overdue" if decision.revisit_date < as_of else "due"
    return DecisionReviewItem(
        decision_id=decision.id,
        signal_id=decision.signal_id,
        original_action=decision.action,
        review_status=status,
        rationale=decision.rationale,
        expected_payoff=decision.expected_payoff,
        risk=decision.risk,
        revisit_date=decision.revisit_date,
        confidence=decision.confidence,
        recommended_action=_recommended_action(decision, status),
    )


def _recommended_action(decision: Decision, status: str) -> str:
    urgency = "overdue" if status == "overdue" else "due"
    return (
        f"Review later: Revisit {decision.action} decision for {decision.signal_id} "
        f"({urgency} {decision.revisit_date}) - {trim_text(decision.rationale, 140)}"
    )


def _summary(items: tuple[DecisionReviewItem, ...], as_of: str) -> str:
    if not items:
        return f"{as_of} 沒有到期決策需要回看；維持現有 radar 觀察即可。"
    overdue = sum(1 for item in items if item.review_status == "overdue")
    due = len(items) - overdue
    first_action = items[0].recommended_action.split(" - ", 1)[0]
    return (
        f"{as_of} 的決策回看判斷是：{len(items)} 個決策需要處理，"
        f"其中 {overdue} 個逾期、{due} 個今天到期。"
        f"最高優先是 {first_action}；先確認原假設是否仍成立，再決定升級、延後或移出 radar。"
    )


def _decision_sort_key(decision: Decision) -> tuple[int, str, str]:
    return (ACTION_RANK.get(decision.action, 9), decision.revisit_date, decision.id)
