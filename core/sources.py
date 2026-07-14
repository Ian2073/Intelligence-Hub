from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class WeightedScores:
    importance: int
    impact: int
    momentum: int
    engineering_value: int
    adoption: int
    longevity: int
    novelty: int

    def score(self) -> int:
        weighted = (
            self.importance * 0.24
            + self.impact * 0.20
            + self.momentum * 0.14
            + self.engineering_value * 0.16
            + self.adoption * 0.10
            + self.longevity * 0.10
            + self.novelty * 0.06
        )
        return round(weighted)


@dataclass(frozen=True)
class PaperSource:
    kind: Literal["paper"]
    title: str
    url: str
    published_at: str
    authors: tuple[str, ...]
    abstract: str
    categories: tuple[str, ...]
    institution: str
    evidence: str
    scores: WeightedScores

    def intelligence_score(self) -> int:
        return self.scores.score()


@dataclass(frozen=True)
class GitHubRepoSource:
    kind: Literal["github_repo"]
    name: str
    url: str
    owner: str
    description: str
    language: str
    stars: int
    topics: tuple[str, ...]
    recent_activity: str
    evidence: str
    scores: WeightedScores

    def intelligence_score(self) -> int:
        return self.scores.score()


@dataclass(frozen=True)
class ArticleSource:
    kind: Literal["article"]
    title: str
    url: str
    published_at: str
    publisher: str
    author: str
    headline: str
    key_claims: tuple[str, ...]
    evidence: str
    scores: WeightedScores

    def intelligence_score(self) -> int:
        return self.scores.score()


@dataclass(frozen=True)
class ReleaseSource:
    kind: Literal["release"]
    product: str
    version: str
    url: str
    published_at: str
    maintainer: str
    changes: tuple[str, ...]
    breaking_changes: tuple[str, ...]
    migration_notes: str
    evidence: str
    scores: WeightedScores

    def intelligence_score(self) -> int:
        return self.scores.score()


@dataclass(frozen=True)
class InternalSeedSource:
    kind: Literal["internal_seed"]
    title: str
    url: str
    published_at: str
    summary: str
    evidence: str
    tags: tuple[str, ...]
    scores: WeightedScores

    def intelligence_score(self) -> int:
        return self.scores.score()


SourceRecord = PaperSource | GitHubRepoSource | ArticleSource | ReleaseSource | InternalSeedSource


def load_source_records(path: Path) -> list[SourceRecord]:
    resolved = path.resolve()
    if not resolved.exists():
        return []
    if not resolved.is_file():
        raise IsADirectoryError(f"Source path is not a file: {resolved}")

    raw = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Source file must contain a JSON array: {resolved}")

    records = [_parse_record(entry, resolved, index) for index, entry in enumerate(raw)]
    return sorted(records, key=lambda item: item.intelligence_score(), reverse=True)


def build_source_context(records: list[SourceRecord], limit: int = 10) -> str:
    if not records:
        return "No typed source records were provided. Treat this as topic-based analysis."

    return "\n\n".join(_format_record(index, record) for index, record in enumerate(records[:limit], start=1))


def source_summary(records: list[SourceRecord]) -> str:
    if not records:
        return "0 typed source records loaded."
    top = records[0]
    return f"{len(records)} typed source records loaded. Top source: {_record_title(top)} ({top.intelligence_score()}/100)."


def _parse_record(entry: Any, path: Path, index: int) -> SourceRecord:
    if not isinstance(entry, dict):
        raise ValueError(f"Source record #{index + 1} in {path} must be an object.")

    kind = _required_str(entry, "kind", path, index)
    scores = _parse_scores(entry.get("scores"), path, index)

    if kind == "paper":
        return PaperSource(
            kind="paper",
            title=_required_str(entry, "title", path, index),
            url=_required_str(entry, "url", path, index),
            published_at=_required_str(entry, "published_at", path, index),
            authors=_str_tuple(entry, "authors"),
            abstract=_required_str(entry, "abstract", path, index),
            categories=_str_tuple(entry, "categories"),
            institution=_optional_str(entry, "institution"),
            evidence=_required_str(entry, "evidence", path, index),
            scores=scores,
        )
    if kind == "github_repo":
        return GitHubRepoSource(
            kind="github_repo",
            name=_required_str(entry, "name", path, index),
            url=_required_str(entry, "url", path, index),
            owner=_required_str(entry, "owner", path, index),
            description=_required_str(entry, "description", path, index),
            language=_optional_str(entry, "language"),
            stars=_int(entry, "stars", path, index),
            topics=_str_tuple(entry, "topics"),
            recent_activity=_required_str(entry, "recent_activity", path, index),
            evidence=_required_str(entry, "evidence", path, index),
            scores=scores,
        )
    if kind == "article":
        return ArticleSource(
            kind="article",
            title=_required_str(entry, "title", path, index),
            url=_required_str(entry, "url", path, index),
            published_at=_required_str(entry, "published_at", path, index),
            publisher=_required_str(entry, "publisher", path, index),
            author=_optional_str(entry, "author"),
            headline=_required_str(entry, "headline", path, index),
            key_claims=_str_tuple(entry, "key_claims"),
            evidence=_required_str(entry, "evidence", path, index),
            scores=scores,
        )
    if kind == "release":
        return ReleaseSource(
            kind="release",
            product=_required_str(entry, "product", path, index),
            version=_required_str(entry, "version", path, index),
            url=_required_str(entry, "url", path, index),
            published_at=_required_str(entry, "published_at", path, index),
            maintainer=_required_str(entry, "maintainer", path, index),
            changes=_str_tuple(entry, "changes"),
            breaking_changes=_str_tuple(entry, "breaking_changes"),
            migration_notes=_optional_str(entry, "migration_notes"),
            evidence=_required_str(entry, "evidence", path, index),
            scores=scores,
        )
    if kind == "internal_seed":
        return InternalSeedSource(
            kind="internal_seed",
            title=_required_str(entry, "title", path, index),
            url=_required_str(entry, "url", path, index),
            published_at=_required_str(entry, "published_at", path, index),
            summary=_required_str(entry, "summary", path, index),
            evidence=_required_str(entry, "evidence", path, index),
            tags=_str_tuple(entry, "tags"),
            scores=scores,
        )

    raise ValueError(f"Source record #{index + 1} in {path} has unsupported kind: {kind!r}")


def _format_record(index: int, record: SourceRecord) -> str:
    score = record.intelligence_score()
    if isinstance(record, PaperSource):
        return "\n".join(
            [
                f"Source {index}: {record.title}",
                "- Kind: paper",
                f"- URL: {record.url}",
                f"- Published: {record.published_at}",
                f"- Authors: {', '.join(record.authors) if record.authors else '(unknown)'}",
                f"- Categories: {', '.join(record.categories) if record.categories else '(none)'}",
                f"- Institution: {record.institution or '(unknown)'}",
                f"- Abstract: {record.abstract}",
                f"- Evidence: {record.evidence}",
                f"- Intelligence Score: {score}/100",
            ]
        )
    if isinstance(record, GitHubRepoSource):
        return "\n".join(
            [
                f"Source {index}: {record.owner}/{record.name}",
                "- Kind: github_repo",
                f"- URL: {record.url}",
                f"- Language: {record.language or '(unknown)'}",
                f"- Stars: {record.stars}",
                f"- Topics: {', '.join(record.topics) if record.topics else '(none)'}",
                f"- Description: {record.description}",
                f"- Recent activity: {record.recent_activity}",
                f"- Evidence: {record.evidence}",
                f"- Intelligence Score: {score}/100",
            ]
        )
    if isinstance(record, ArticleSource):
        return "\n".join(
            [
                f"Source {index}: {record.title}",
                "- Kind: article",
                f"- URL: {record.url}",
                f"- Published: {record.published_at}",
                f"- Publisher: {record.publisher}",
                f"- Author: {record.author or '(unknown)'}",
                f"- Headline: {record.headline}",
                f"- Key claims: {'; '.join(record.key_claims) if record.key_claims else '(none)'}",
                f"- Evidence: {record.evidence}",
                f"- Intelligence Score: {score}/100",
            ]
        )
    if isinstance(record, ReleaseSource):
        return "\n".join(
            [
                f"Source {index}: {record.product} {record.version}",
                "- Kind: release",
                f"- URL: {record.url}",
                f"- Published: {record.published_at}",
                f"- Maintainer: {record.maintainer}",
                f"- Changes: {'; '.join(record.changes) if record.changes else '(none)'}",
                f"- Breaking changes: {'; '.join(record.breaking_changes) if record.breaking_changes else '(none)'}",
                f"- Migration notes: {record.migration_notes or '(none)'}",
                f"- Evidence: {record.evidence}",
                f"- Intelligence Score: {score}/100",
            ]
        )
    return "\n".join(
        [
            f"Source {index}: {record.title}",
            "- Kind: internal_seed",
            f"- URL: {record.url}",
            f"- Published: {record.published_at}",
            f"- Tags: {', '.join(record.tags) if record.tags else '(none)'}",
            f"- Summary: {record.summary}",
            f"- Evidence: {record.evidence}",
            f"- Intelligence Score: {score}/100",
        ]
    )


def _record_title(record: SourceRecord) -> str:
    if isinstance(record, GitHubRepoSource):
        return f"{record.owner}/{record.name}"
    if isinstance(record, ReleaseSource):
        return f"{record.product} {record.version}"
    return record.title


def _parse_scores(value: Any, path: Path, index: int) -> WeightedScores:
    if not isinstance(value, dict):
        raise ValueError(f"Source record #{index + 1} in {path} has invalid scores.")
    return WeightedScores(
        importance=_score(value, "importance", path, index),
        impact=_score(value, "impact", path, index),
        momentum=_score(value, "momentum", path, index),
        engineering_value=_score(value, "engineering_value", path, index),
        adoption=_score(value, "adoption", path, index),
        longevity=_score(value, "longevity", path, index),
        novelty=_score(value, "novelty", path, index),
    )


def _required_str(entry: dict, key: str, path: Path, index: int) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Source record #{index + 1} in {path} must include non-empty {key!r}.")
    return value.strip()


def _optional_str(entry: dict, key: str) -> str:
    value = entry.get(key)
    return value.strip() if isinstance(value, str) else ""


def _str_tuple(entry: dict, key: str) -> tuple[str, ...]:
    value = entry.get(key, [])
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _int(entry: dict, key: str, path: Path, index: int) -> int:
    value = entry.get(key)
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"Source record #{index + 1} in {path} must include non-negative integer {key!r}.")
    return value


def _score(scores: dict, key: str, path: Path, index: int) -> int:
    value = scores.get(key)
    if not isinstance(value, int) or value < 0 or value > 100:
        raise ValueError(f"Source record #{index + 1} in {path} must include score {key!r} from 0 to 100.")
    return value
