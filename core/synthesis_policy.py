from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


SynthesisMode = Literal["off", "hybrid", "full"]
SynthesisTier = Literal["deterministic", "fast", "pro"]


DEFAULT_TASK_TIERS: dict[str, SynthesisTier] = {
    "daily_executive_summary": "pro",
    "top_decision_rationale": "pro",
    "weekly_synthesis": "pro",
    "monthly_synthesis": "pro",
    "radar_entity": "deterministic",
    "cross_signal_insight": "deterministic",
}


@dataclass
class SynthesisUsage:
    pro_calls_used: int = 0
    fast_calls_used: int = 0
    deterministic_calls: int = 0
    fallback_count: int = 0


@dataclass
class SynthesisPolicy:
    mode: SynthesisMode = "hybrid"
    pro_call_limit: int = 8
    task_tiers: dict[str, SynthesisTier] | None = None
    usage: SynthesisUsage | None = None

    @classmethod
    def from_env(cls) -> "SynthesisPolicy":
        mode = os.getenv("HERMES_SYNTHESIS_MODE", "hybrid").strip().lower()
        if mode not in {"off", "hybrid", "full"}:
            mode = "hybrid"
        limit = _env_int("HERMES_PRO_CALL_LIMIT", 8)
        return cls(mode=mode, pro_call_limit=max(0, limit))

    def __post_init__(self) -> None:
        if self.task_tiers is None:
            self.task_tiers = dict(DEFAULT_TASK_TIERS)
        if self.usage is None:
            self.usage = SynthesisUsage()

    def tier_for(self, task: str) -> SynthesisTier:
        clean = task.strip().lower().replace(" ", "_")
        if self.mode == "off":
            self.usage.deterministic_calls += 1
            return "deterministic"
        tier = (self.task_tiers or DEFAULT_TASK_TIERS).get(clean, "fast" if self.mode == "full" else "deterministic")
        if tier == "pro":
            if self.usage.pro_calls_used >= self.pro_call_limit:
                self.usage.deterministic_calls += 1
                self.usage.fallback_count += 1
                return "deterministic"
            self.usage.pro_calls_used += 1
            return "pro"
        if tier == "fast":
            self.usage.fast_calls_used += 1
            return "fast"
        self.usage.deterministic_calls += 1
        return "deterministic"

    def record_fallback(self) -> None:
        self.usage.fallback_count += 1


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default
