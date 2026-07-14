from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx

from connectors.retry import retry_on_transient

from contracts.watchlist import DomainWatchItem
from connectors.domain import DomainSignalSnapshot


class DomainRssError(RuntimeError):
    pass


DEPTH_SIGNALS = {
    "architecture",
    "benchmark",
    "benchmarks",
    "eval",
    "evaluation",
    "inference",
    "quantization",
    "fine-tuning",
    "finetuning",
    "retrieval",
    "rag",
    "embedding",
    "embeddings",
    "vector database",
    "knowledge graph",
    "mcp",
    "function calling",
    "tool use",
    "reasoning",
    "multimodal",
    "vlm",
}

ACTION_SIGNALS = {
    "available",
    "api",
    "beta",
    "developer preview",
    "framework",
    "github",
    "launch",
    "open source",
    "released",
    "release",
    "sdk",
    "toolkit",
    "v2",
    "v3",
    "v4",
}

SCOPE_SIGNALS = {
    "ecosystem",
    "infrastructure",
    "industry",
    "platform",
    "standard",
    "supply chain",
    "market",
    "enterprise",
    "developers",
    "cloud",
}

RECENCY_SIGNALS = {
    "announced",
    "today",
    "new",
    "now",
    "this week",
    "launched",
    "released",
    "ships",
    "rolling out",
}

LOW_VALUE_SIGNALS = {
    "opinion",
    "prediction",
    "roundup",
    "recap",
    "rumor",
    "sponsored",
    "advertisement",
    "guide",
}

TECHNOLOGY_PATTERNS = (
    ("AI agents", ("agent", "agents", "agentic")),
    ("Inference", ("inference", "serving", "gpu", "latency", "throughput")),
    ("Security evals", ("security", "prompt injection", "red team", "vulnerab", "exploit")),
    ("Local inference", ("local model", "on-device", "edge inference", "local inference")),
    ("RAG", ("rag", "retrieval augmented", "retrieval-augmented")),
    ("MCP", ("mcp", "model context protocol")),
    ("Function calling", ("function calling", "tool calling", "structured tool")),
    ("Fine-tuning", ("fine-tuning", "finetuning", "lora", "adapter tuning")),
    ("Quantization", ("quantization", "quantized", "int4", "int8", "gguf")),
    ("RLHF", ("rlhf", "reinforcement learning from human feedback")),
    ("Reasoning", ("reasoning", "chain-of-thought", "cot")),
    ("Code generation", ("code generation", "coding agent", "code editing", "developer tool")),
    ("Multimodal", ("multimodal", "vision-language", "vlm", "image understanding")),
    ("Embeddings", ("embedding", "embeddings")),
    ("Vector DB", ("vector database", "vector db", "semantic search")),
    ("Knowledge graphs", ("knowledge graph", "graph rag")),
    ("Prompt engineering", ("prompt engineering", "prompting")),
)

COMPANY_NAMES = (
    "OpenAI",
    "Anthropic",
    "Google",
    "Meta",
    "NVIDIA",
    "Apple",
    "Microsoft",
    "Amazon",
    "Mistral",
    "Cohere",
    "Databricks",
    "Hugging Face",
    "Together AI",
    "xAI",
    "DeepSeek",
    "Groq",
    "Cerebras",
)


@dataclass(frozen=True)
class DomainRssClient:
    timeout: float = 30.0

    def fetch(self, item: DomainWatchItem, observed_at: str) -> list[DomainSignalSnapshot]:
        if not item.rss_url:
            raise DomainRssError(f"Domain watch item has no rss_url: {item.domain}/{item.name}")
        try:
            response = retry_on_transient(
                lambda: httpx.get(item.rss_url, timeout=self.timeout, follow_redirects=True),
                operation_name="Domain RSS",
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise DomainRssError(f"RSS feed returned HTTP {exc.response.status_code}: {exc.response.text[:300]}") from exc
        except Exception as exc:
            raise DomainRssError(f"RSS feed request failed: {exc}") from exc
        return parse_domain_rss_feed(response.text, item, observed_at)


def parse_domain_rss_feed(feed_xml: str, item: DomainWatchItem, observed_at: str) -> list[DomainSignalSnapshot]:
    try:
        root = ET.fromstring(feed_xml)
    except ET.ParseError as exc:
        raise DomainRssError(f"RSS feed is not valid XML: {exc}") from exc

    entries = _atom_entries(root) or _rss_entries(root)
    snapshots = []
    for entry in entries[: item.max_results]:
        title = _clean_text(_entry_value(entry, ("title", "{http://www.w3.org/2005/Atom}title")))
        url = _clean_text(
            _entry_value(entry, ("link", "{http://www.w3.org/2005/Atom}id", "guid"))
            or _atom_link_href(entry)
            or item.rss_url
        )
        published_at = _clean_text(
            _entry_value(
                entry,
                (
                    "pubDate",
                    "published",
                    "updated",
                    "{http://www.w3.org/2005/Atom}published",
                    "{http://www.w3.org/2005/Atom}updated",
                ),
            )
            or observed_at
        )
        summary = _clean_text(
            _entry_value(
                entry,
                (
                    "description",
                    "summary",
                    "content",
                    "{http://www.w3.org/2005/Atom}summary",
                    "{http://www.w3.org/2005/Atom}content",
                ),
            )
            or title
        )
        if not title:
            continue
        snapshots.append(
            DomainSignalSnapshot(
                domain=item.domain,
                title=title,
                entity_name=item.name,
                entity_kind="trend",
                source_url=url,
                published_at=published_at,
                summary=summary,
                evidence=f"RSS item from {item.rss_url}: {title}",
                impact_score=_impact_score(title, summary),
                confidence="medium",
                tags=("rss", item.domain),
                technologies=_infer_technologies(title, summary),
                companies=_infer_companies(title, summary),
                repositories=(),
                observed_at=observed_at,
                recommended_action="",
            )
        )
    return snapshots


def _rss_entries(root: ET.Element) -> list[ET.Element]:
    channel = root.find("channel")
    if channel is None:
        return []
    return list(channel.findall("item"))


def _atom_entries(root: ET.Element) -> list[ET.Element]:
    return list(root.findall("{http://www.w3.org/2005/Atom}entry"))


def _entry_value(entry: ET.Element, names: tuple[str, ...]) -> str:
    for name in names:
        child = entry.find(name)
        if child is not None and child.text and child.text.strip():
            return child.text
    return ""


def _atom_link_href(entry: ET.Element) -> str:
    for link in entry.findall("{http://www.w3.org/2005/Atom}link"):
        href = link.attrib.get("href", "").strip()
        if href:
            return href
    return ""


def _clean_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", without_tags).strip()


def _impact_score(title: str, summary: str) -> int:
    text = f"{title} {summary}".casefold()
    depth = _dimension_score(text, DEPTH_SIGNALS)
    actionability = _dimension_score(text, ACTION_SIGNALS)
    scope = _dimension_score(text, SCOPE_SIGNALS)
    recency = _dimension_score(text, RECENCY_SIGNALS)

    score = int(20 + depth * 0.30 + actionability * 0.25 + scope * 0.25 + recency * 0.20)
    if any(company.casefold() in text for company in COMPANY_NAMES):
        score += 5
    if any(term in text for term in ("breakthrough", "acquisition", "funding", "vulnerable", "exploit")):
        score += 6
    if len(title) <= 80:
        score += 3
    if any(keyword in text for keyword in LOW_VALUE_SIGNALS):
        score -= 10
    return max(min(score, 95), 20)


def _dimension_score(text: str, signals: set[str]) -> int:
    hits = sum(1 for keyword in signals if keyword in text)
    if hits >= 4:
        return 95
    if hits == 3:
        return 80
    if hits == 2:
        return 60
    if hits == 1:
        return 40
    return 15


def _infer_technologies(title: str, summary: str) -> tuple[str, ...]:
    text = f"{title} {summary}".casefold()
    technologies = []
    for label, patterns in TECHNOLOGY_PATTERNS:
        if any(pattern in text for pattern in patterns):
            technologies.append(label)
    return tuple(technologies)


def _infer_companies(title: str, summary: str) -> tuple[str, ...]:
    text = f"{title} {summary}".casefold()
    companies = []
    for name in COMPANY_NAMES:
        if name.casefold() in text:
            companies.append(name)
    return tuple(companies)
