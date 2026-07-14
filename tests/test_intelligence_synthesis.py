from __future__ import annotations

from core.intelligence_synthesis import (
    synthesize_daily_summary,
    synthesize_dashboard_summary,
    synthesize_period_summary,
    synthesize_weekly_summary,
)


class FakeRouter:
    def __init__(self) -> None:
        self.calls = []

    def generate(self, prompt, *, tier="fast"):
        self.calls.append((prompt, tier))
        return "Model summary. Top posture: Prototype."


class FailingRouter:
    def generate(self, prompt, *, tier="fast"):
        raise RuntimeError("cloud unavailable")


def test_synthesize_daily_summary_uses_pro_tier_when_router_is_provided() -> None:
    router = FakeRouter()

    summary = synthesize_daily_summary(
        title="Hermes Daily Intelligence - 2026-07-02",
        fallback_summary="Fallback summary.",
        decisions=("Prototype: Important signal.",),
        router=router,
    )

    assert summary == "Model summary. Top posture: Prototype."
    assert router.calls[0][1] == "pro"
    assert "Do not dump information." in router.calls[0][0]
    assert "Write in Traditional Chinese." in router.calls[0][0]
    assert "Do not introduce diagnoses" in router.calls[0][0]
    assert "Preserve concrete action targets" in router.calls[0][0]


def test_synthesize_weekly_summary_falls_back_without_router() -> None:
    assert (
        synthesize_weekly_summary(
            title="Weekly",
            fallback_summary="Fallback weekly summary.",
            trends=("Agent: Up",),
            top_actions=("Read: Something",),
            router=None,
        )
        == "Fallback weekly summary."
    )


def test_synthesize_period_and_dashboard_use_pro_tier() -> None:
    period_router = FakeRouter()
    dashboard_router = FakeRouter()

    assert synthesize_period_summary(
        title="Monthly",
        fallback_summary="Fallback monthly.",
        trends=("Agents: Up",),
        top_actions=("Prototype: Something",),
        router=period_router,
    ) == "Model summary. Top posture: Prototype."
    assert synthesize_dashboard_summary(
        title="Dashboard",
        fallback_summary="Fallback dashboard.",
        latest_items=("Daily: Today",),
        top_actions=("Read: Something",),
        router=dashboard_router,
    ) == "Model summary. Top posture: Prototype."

    assert period_router.calls[0][1] == "pro"
    assert dashboard_router.calls[0][1] == "pro"


def test_synthesize_daily_summary_falls_back_when_router_fails(caplog) -> None:
    summary = synthesize_daily_summary(
        title="Hermes Daily Intelligence - 2026-07-09",
        fallback_summary="Fallback summary.",
        decisions=("Prototype: Important signal.",),
        router=FailingRouter(),
    )

    assert summary == "Fallback summary."
    assert "Synthesis failed; using fallback summary." in caplog.text
