from __future__ import annotations

from typing import Literal


ModelTier = Literal["fast", "pro"]


FAST_TASKS: frozenset[str] = frozenset(
    {
        "source_normalization",
        "classification",
        "deduplication",
        "short_summary",
        "telegram_copy",
    }
)

PRO_TASKS: frozenset[str] = frozenset(
    {
        "daily_decision",
        "weekly_synthesis",
        "monthly_synthesis",
        "executive_dashboard",
        "research_brief",
        "decision_review",
    }
)


def tier_for_task(task: str) -> ModelTier:
    clean = task.strip().lower().replace(" ", "_")
    if clean in PRO_TASKS:
        return "pro"
    return "fast"
