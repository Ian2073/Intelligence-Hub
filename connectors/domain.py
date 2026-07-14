from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class DomainSignalError(RuntimeError):
    pass


@dataclass(frozen=True)
class DomainSignalSnapshot:
    domain: str
    title: str
    entity_name: str
    entity_kind: str
    source_url: str
    published_at: str
    summary: str
    evidence: str
    impact_score: int
    confidence: str
    tags: tuple[str, ...]
    technologies: tuple[str, ...]
    companies: tuple[str, ...]
    repositories: tuple[str, ...]
    observed_at: str
    recommended_action: str


def parse_domain_signal_snapshot(data: dict[str, Any], observed_at: str) -> DomainSignalSnapshot:
    impact_score = _int(data, "impact_score")
    if impact_score < 0 or impact_score > 100:
        raise DomainSignalError("Domain signal impact_score must be between 0 and 100.")
    return DomainSignalSnapshot(
        domain=_required_str(data, "domain"),
        title=_required_str(data, "title"),
        entity_name=_required_str(data, "entity_name"),
        entity_kind=str(data.get("entity_kind") or "trend").strip(),
        source_url=_required_str(data, "source_url"),
        published_at=_required_str(data, "published_at"),
        summary=_required_str(data, "summary"),
        evidence=_required_str(data, "evidence"),
        impact_score=impact_score,
        confidence=str(data.get("confidence") or "medium").strip(),
        tags=_str_tuple(data.get("tags")),
        technologies=_str_tuple(data.get("technologies")),
        companies=_str_tuple(data.get("companies")),
        repositories=_str_tuple(data.get("repositories")),
        observed_at=observed_at.strip(),
        recommended_action=str(data.get("recommended_action") or "").strip(),
    )


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DomainSignalError(f"Domain signal payload must include non-empty {key!r}.")
    return value.strip()


def _int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise DomainSignalError(f"Domain signal payload must include integer {key!r}.")
    return value


def _str_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())
