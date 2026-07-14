from __future__ import annotations

import logging
from typing import Protocol

from core.model_policy import tier_for_task

logger = logging.getLogger(__name__)


class TieredGenerator(Protocol):
    def generate(self, prompt: str, *, tier: str = "fast") -> str:
        ...


def synthesize_daily_summary(
    *,
    title: str,
    fallback_summary: str,
    decisions: tuple[str, ...],
    router: TieredGenerator | None = None,
) -> str:
    if router is None or not decisions:
        return fallback_summary
    prompt = _summary_prompt(
        title=title,
        fallback_summary=fallback_summary,
        decisions=decisions,
        period="today",
    )
    return _generate_summary(router, prompt, tier=tier_for_task("daily_decision"), fallback_summary=fallback_summary)


def synthesize_weekly_summary(
    *,
    title: str,
    fallback_summary: str,
    trends: tuple[str, ...],
    top_actions: tuple[str, ...],
    router: TieredGenerator | None = None,
) -> str:
    if router is None or (not trends and not top_actions):
        return fallback_summary
    prompt = _summary_prompt(
        title=title,
        fallback_summary=fallback_summary,
        decisions=(*trends, *top_actions),
        period="this week",
    )
    return _generate_summary(router, prompt, tier=tier_for_task("weekly_synthesis"), fallback_summary=fallback_summary)


def synthesize_period_summary(
    *,
    title: str,
    fallback_summary: str,
    trends: tuple[str, ...],
    top_actions: tuple[str, ...],
    router: TieredGenerator | None = None,
) -> str:
    if router is None or (not trends and not top_actions):
        return fallback_summary
    prompt = _summary_prompt(
        title=title,
        fallback_summary=fallback_summary,
        decisions=(*trends, *top_actions),
        period="this period",
    )
    return _generate_summary(router, prompt, tier=tier_for_task("monthly_synthesis"), fallback_summary=fallback_summary)


def synthesize_dashboard_summary(
    *,
    title: str,
    fallback_summary: str,
    latest_items: tuple[str, ...],
    top_actions: tuple[str, ...],
    router: TieredGenerator | None = None,
) -> str:
    if router is None or (not latest_items and not top_actions):
        return fallback_summary
    prompt = _summary_prompt(
        title=title,
        fallback_summary=fallback_summary,
        decisions=(*latest_items, *top_actions),
        period="the executive dashboard",
    )
    return _generate_summary(router, prompt, tier=tier_for_task("executive_dashboard"), fallback_summary=fallback_summary)


def _generate_summary(
    router: TieredGenerator,
    prompt: str,
    *,
    tier: str,
    fallback_summary: str,
) -> str:
    try:
        return _clean_summary(router.generate(prompt, tier=tier), fallback_summary)
    except Exception as exc:
        logger.warning("Synthesis failed; using fallback summary. Reason: %s", exc)
        logger.debug("Synthesis fallback traceback.", exc_info=True)
        return fallback_summary


def _summary_prompt(
    *,
    title: str,
    fallback_summary: str,
    decisions: tuple[str, ...],
    period: str,
) -> str:
    decision_lines = "\n".join(f"- {line}" for line in decisions[:10])
    return f"""You are Hermes Intelligence OS.

Task: write one concise executive summary for {period}.

Rules:
- Do not dump information.
- Make a judgment.
- Keep it under 90 words.
- Mention only evidence provided below.
- Write in Traditional Chinese.
- Do not introduce diagnoses, causes, or recommendations that are not directly supported by the evidence.
- Preserve concrete action targets and next steps when they are present.
- End with the most important action posture.

Title:
{title}

Fallback summary:
{fallback_summary}

Evidence:
{decision_lines}
"""


def _clean_summary(candidate: str, fallback: str) -> str:
    text = " ".join(candidate.strip().split())
    if not text:
        return fallback
    return text[:1200]
