from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CrossSignalInsight:
    title: str
    subject: str
    sources: tuple[str, ...]
    rationale: str
    confidence: str


def analyze_cross_signals(
    repo_results,
    paper_results,
    domain_results,
    store=None,
) -> tuple[CrossSignalInsight, ...]:
    buckets: dict[str, dict] = {}
    for result in repo_results:
        for term in _repo_terms(result):
            _add_hit(buckets, term, "GitHub", result.entity.canonical_name, _repo_detail(result))
    for result in paper_results:
        for term in _paper_terms(result):
            _add_hit(buckets, term, "Paper", result.entity.canonical_name, _paper_detail(result))
    for result in domain_results:
        for term in _domain_terms(result):
            _add_hit(buckets, term, "Domain", result.entity.canonical_name, _domain_detail(result))

    insights = []
    for subject, bucket in buckets.items():
        sources = tuple(sorted(bucket["sources"]))
        if len(sources) < 2:
            continue
        entities = tuple(dict.fromkeys(bucket["entities"]))
        details = tuple(dict.fromkeys(bucket["details"]))
        source_label = " + ".join(sources)
        rationale = (
            f"{subject} 同時出現在 {source_label} 訊號中；"
            f"相關 entity 包含 {', '.join(entities[:4])}。"
        )
        if details:
            rationale += f" 交叉證據：{'；'.join(details[:3])}。"
        confidence = "high" if len(sources) >= 3 else "medium"
        insights.append(
            CrossSignalInsight(
                title=f"{subject} 生態系加速",
                subject=subject,
                sources=sources,
                rationale=rationale,
                confidence=confidence,
            )
        )
    return tuple(sorted(insights, key=lambda item: (-len(item.sources), item.subject)))[:5]


def _add_hit(buckets: dict[str, dict], term: str, source: str, entity: str, detail: str) -> None:
    normalized = _normalize(term)
    if not normalized or normalized in {"ai", "llm", "github", "paper", "rss"}:
        return
    bucket = buckets.setdefault(
        normalized,
        {"sources": set(), "entities": [], "details": [], "display": term},
    )
    bucket["sources"].add(source)
    bucket["entities"].append(entity)
    if detail:
        bucket["details"].append(detail)


def _repo_terms(result) -> tuple[str, ...]:
    tags = tuple(tag for tag in result.entity.tags if tag != "github")
    return tuple(_display_term(tag) for tag in tags)


def _paper_terms(result) -> tuple[str, ...]:
    tags = tuple(tag for tag in result.entity.tags if tag not in {"paper", "cs.AI", "cs.CL", "cs.SE", "cs.IR"})
    relationship_terms = tuple(_relationship_term(rel) for rel in getattr(result, "relationships", ()))
    return tuple(_display_term(term) for term in (*tags, *relationship_terms) if term)


def _domain_terms(result) -> tuple[str, ...]:
    tags = tuple(tag for tag in result.entity.tags if tag not in {"rss"})
    relationship_terms = tuple(_relationship_term(rel) for rel in getattr(result, "relationships", ()))
    return tuple(_display_term(term) for term in (*tags, *relationship_terms) if term)


def _repo_detail(result) -> str:
    return f"{result.entity.canonical_name} {result.star_delta:+d} stars / {result.momentum}"


def _paper_detail(result) -> str:
    return f"{result.entity.canonical_name} links {len(getattr(result, 'relationships', ()))} radar entities"


def _domain_detail(result) -> str:
    return f"{result.signal_title} impact {result.priority_score}"


def _display_term(term: str) -> str:
    replacements = {
        "domain_related_technology": "",
        "domain_related_company": "",
        "domain_related_repository": "",
        "uses_or_advances": "",
        "related_repository": "",
        "related_company": "",
    }
    return replacements.get(term, term).strip()


def _relationship_term(relationship) -> str:
    evidence = getattr(relationship, "evidence", "")
    match = re.search(r"\bto\s+([^.:]+)", evidence)
    if match:
        return match.group(1).strip()
    match = re.search(r":\s*([^.:]+)", evidence)
    if match:
        return match.group(1).strip()
    return ""


def _normalize(term: str) -> str:
    normalized = term.casefold().replace("_", " ").replace("-", " ").strip()
    aliases = {
        "agent": "ai agents",
        "agents": "ai agents",
        "ai agent": "ai agents",
        "ai agents": "ai agents",
        "rag": "rag",
        "retrieval augmented generation": "rag",
        "retrieval": "rag",
        "inference": "inference",
        "local inference": "inference",
        "quantization": "quantization",
        "security evals": "security evals",
        "tool use": "tool use",
        "tool calling": "tool use",
        "function calling": "tool use",
        "multimodal": "multimodal",
        "vision language models": "multimodal",
    }
    return aliases.get(normalized, normalized)
