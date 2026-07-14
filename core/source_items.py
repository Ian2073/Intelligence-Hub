from __future__ import annotations

from dataclasses import dataclass

from core.sources import WeightedScores


@dataclass(frozen=True)
class SourceItem:
    title: str
    source_type: str
    url: str
    published_at: str
    summary: str
    evidence: str
    tags: tuple[str, ...]
    importance: int
    impact: int
    momentum: int
    engineering_value: int
    adoption: int
    longevity: int
    novelty: int

    @property
    def kind(self) -> str:
        return "internal_seed"

    @property
    def scores(self) -> WeightedScores:
        return WeightedScores(
            importance=self.importance,
            impact=self.impact,
            momentum=self.momentum,
            engineering_value=self.engineering_value,
            adoption=self.adoption,
            longevity=self.longevity,
            novelty=self.novelty,
        )

    def intelligence_score(self) -> int:
        return self.scores.score()
