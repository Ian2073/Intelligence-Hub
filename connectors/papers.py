from __future__ import annotations

import re
import urllib.parse
import xml.etree.ElementTree as ET
from html import unescape
from dataclasses import dataclass
from typing import Any

import httpx

from connectors.retry import retry_on_transient


class PaperError(RuntimeError):
    pass


@dataclass(frozen=True)
class PaperSnapshot:
    title: str
    url: str
    published_at: str
    authors: tuple[str, ...]
    abstract: str
    categories: tuple[str, ...]
    technologies: tuple[str, ...]
    repositories: tuple[str, ...]
    companies: tuple[str, ...]
    observed_at: str


class ArxivClient:
    def __init__(self, base_url: str = "https://export.arxiv.org/api/query", timeout: float = 30.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def search(self, query: str, observed_at: str, max_results: int = 5) -> list[PaperSnapshot]:
        params = {
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": str(max_results),
        }
        url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        try:
            response = retry_on_transient(
                lambda: httpx.get(url, timeout=self.timeout),
                operation_name="arXiv API",
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise PaperError(f"arXiv returned HTTP {exc.response.status_code}: {exc.response.text[:300]}") from exc
        except Exception as exc:
            raise PaperError(f"arXiv request failed: {exc}") from exc
        return parse_arxiv_feed(response.text, observed_at)


class PapersWithCodeClient:
    def __init__(
        self,
        base_url: str = "https://paperswithcode.com/api/v1",
        timeout: float = 30.0,
        fallback_url: str = "https://huggingface.co/papers/trending",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.fallback_url = fallback_url

    def search(self, query: str, observed_at: str, max_results: int = 5) -> list[PaperSnapshot]:
        params = {"q": query, "page_size": str(max_results)}
        url = f"{self.base_url}/papers/?{urllib.parse.urlencode(params)}"
        try:
            response = retry_on_transient(
                lambda: httpx.get(url, timeout=self.timeout, follow_redirects=False),
                operation_name="Papers with Code API",
            )
            if response.status_code in {301, 302, 307, 308}:
                location = response.headers.get("location", "")
                if "huggingface.co/papers" in location:
                    return self._search_huggingface_papers(query, observed_at, max_results)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise PaperError(
                f"Papers with Code returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except Exception as exc:
            raise PaperError(f"Papers with Code request failed: {exc}") from exc
        except ValueError as exc:
            raise PaperError("Papers with Code returned invalid JSON.") from exc

        snapshots = parse_papers_with_code_response(payload, observed_at)
        enriched = []
        for snapshot, paper_id in zip(snapshots, _paper_ids(payload), strict=False):
            repositories = snapshot.repositories
            if paper_id:
                repositories = tuple(dict.fromkeys((*repositories, *self._fetch_repositories(paper_id))))
            enriched.append(
                PaperSnapshot(
                    title=snapshot.title,
                    url=snapshot.url,
                    published_at=snapshot.published_at,
                    authors=snapshot.authors,
                    abstract=snapshot.abstract,
                    categories=snapshot.categories,
                    technologies=snapshot.technologies,
                    repositories=repositories,
                    companies=snapshot.companies,
                    observed_at=snapshot.observed_at,
                )
            )
        return enriched

    def _search_huggingface_papers(
        self,
        query: str,
        observed_at: str,
        max_results: int,
    ) -> list[PaperSnapshot]:
        try:
            response = retry_on_transient(
                lambda: httpx.get(self.fallback_url, timeout=self.timeout),
                operation_name="Hugging Face Papers",
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise PaperError(
                f"Hugging Face Papers returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except Exception as exc:
            raise PaperError(f"Hugging Face Papers request failed: {exc}") from exc
        snapshots = parse_huggingface_papers_page(response.text, observed_at)
        query_terms = tuple(term for term in re.split(r"\W+", query.casefold()) if len(term) >= 3)
        ranked = sorted(snapshots, key=lambda snapshot: _query_match_score(snapshot, query_terms), reverse=True)
        matched = [snapshot for snapshot in ranked if _query_match_score(snapshot, query_terms) > 0]
        return (matched or ranked)[:max_results]

    def _fetch_repositories(self, paper_id: str) -> tuple[str, ...]:
        url = f"{self.base_url}/papers/{urllib.parse.quote(paper_id, safe='')}/repositories/"
        try:
            response = retry_on_transient(
                lambda: httpx.get(url, timeout=self.timeout),
                operation_name="Papers with Code Repos",
            )
            response.raise_for_status()
            payload = response.json()
        except (Exception, ValueError):
            return ()
        return _repositories_from_pwc_payload(payload)


def parse_paper_snapshot(data: dict[str, Any], observed_at: str) -> PaperSnapshot:
    return PaperSnapshot(
        title=_required_str(data, "title"),
        url=_required_str(data, "url"),
        published_at=_required_str(data, "published_at"),
        authors=_str_tuple(data.get("authors")),
        abstract=_required_str(data, "abstract"),
        categories=_str_tuple(data.get("categories")),
        technologies=_str_tuple(data.get("technologies")),
        repositories=_str_tuple(data.get("repositories")),
        companies=_str_tuple(data.get("companies")),
        observed_at=observed_at.strip(),
    )


def parse_papers_with_code_response(payload: dict[str, Any], observed_at: str) -> list[PaperSnapshot]:
    results = payload.get("results")
    if not isinstance(results, list):
        raise PaperError("Papers with Code payload must include a results list.")
    return [_parse_papers_with_code_paper(result, observed_at) for result in results if isinstance(result, dict)]


def parse_huggingface_papers_page(html: str, observed_at: str) -> list[PaperSnapshot]:
    text = unescape(html)
    records = []
    for match in re.finditer(r'"id":"(?P<id>\d{4}\.\d{4,5})"', text):
        start = match.start()
        next_match = re.search(r'"id":"\d{4}\.\d{4,5}"', text[match.end() :])
        end = match.end() + next_match.start() if next_match else min(len(text), start + 20000)
        block = text[start:end]
        title = _json_string_field(block, "title")
        summary = _json_string_field(block, "ai_summary") or _json_string_field(block, "summary")
        if not title or not summary:
            continue
        arxiv_id = match.group("id")
        published_at = (_json_string_field(block, "publishedAt") or observed_at).split("T", 1)[0]
        github_repo = _github_repo_name(_json_string_field(block, "githubRepo"))
        authors = tuple(re.findall(r'"name":"([^"]+?)","hidden":false', block))[:8]
        categories = tuple(re.findall(r'"ai_keywords":\[(.*?)\]', block))
        keyword_values = _json_array_values(categories[0]) if categories else ()
        records.append(
            PaperSnapshot(
                title=_clean_text(title),
                url=f"https://arxiv.org/abs/{arxiv_id}",
                published_at=published_at,
                authors=authors,
                abstract=_clean_text(summary),
                categories=keyword_values,
                technologies=_infer_technologies(title, summary, keyword_values),
                repositories=(github_repo,) if github_repo else (),
                companies=_infer_companies(title, summary),
                observed_at=observed_at.strip(),
            )
        )
    return tuple(dict.fromkeys(records))


def parse_arxiv_feed(feed_xml: str, observed_at: str) -> list[PaperSnapshot]:
    try:
        root = ET.fromstring(feed_xml)
    except ET.ParseError as exc:
        raise PaperError(f"arXiv feed is not valid XML: {exc}") from exc

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    snapshots = []
    for entry in root.findall("atom:entry", ns):
        title = _entry_text(entry, "atom:title", ns)
        url = _entry_text(entry, "atom:id", ns)
        published_at = _entry_text(entry, "atom:published", ns)
        abstract = _entry_text(entry, "atom:summary", ns)
        authors = tuple(
            _clean_text(author.findtext("atom:name", default="", namespaces=ns))
            for author in entry.findall("atom:author", ns)
        )
        categories = tuple(
            category.attrib.get("term", "").strip()
            for category in entry.findall("atom:category", ns)
            if category.attrib.get("term", "").strip()
        )
        snapshots.append(
            PaperSnapshot(
                title=_clean_text(title),
                url=url.strip(),
                published_at=published_at.strip(),
                authors=tuple(author for author in authors if author),
                abstract=_clean_text(abstract),
                categories=categories,
                technologies=_infer_technologies(title, abstract, categories),
                repositories=(),
                companies=_infer_companies(title, abstract),
                observed_at=observed_at.strip(),
            )
        )
    return snapshots


def _parse_papers_with_code_paper(data: dict[str, Any], observed_at: str) -> PaperSnapshot:
    title = str(data.get("title") or "").strip()
    if not title:
        raise PaperError("Papers with Code paper is missing title.")
    abstract = _clean_text(str(data.get("abstract") or data.get("summary") or "No abstract provided."))
    categories = _pwc_categories(data)
    repositories = _repositories_from_pwc_payload(data)
    return PaperSnapshot(
        title=title,
        url=_pwc_paper_url(data),
        published_at=str(data.get("published") or data.get("published_at") or data.get("date") or observed_at).strip(),
        authors=_pwc_authors(data.get("authors")),
        abstract=abstract,
        categories=categories,
        technologies=_infer_technologies(title, abstract, categories),
        repositories=repositories,
        companies=_infer_companies(title, abstract),
        observed_at=observed_at.strip(),
    )


def _pwc_paper_url(data: dict[str, Any]) -> str:
    for key in ("url_abs", "paper_url", "url", "url_pdf"):
        value = str(data.get(key) or "").strip()
        if value:
            return value
    arxiv_id = str(data.get("arxiv_id") or "").strip()
    if arxiv_id:
        return f"https://arxiv.org/abs/{arxiv_id}"
    paper_id = str(data.get("id") or "").strip()
    if paper_id:
        return f"https://paperswithcode.com/paper/{paper_id}"
    raise PaperError("Papers with Code paper is missing a usable URL.")


def _pwc_authors(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    authors = []
    for item in value:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("full_name") or "").strip()
        else:
            name = str(item).strip()
        if name:
            authors.append(name)
    return tuple(authors)


def _pwc_categories(data: dict[str, Any]) -> tuple[str, ...]:
    categories = []
    for key in ("tasks", "methods", "datasets"):
        value = data.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    name = str(item.get("name") or item.get("task") or "").strip()
                else:
                    name = str(item).strip()
                if name:
                    categories.append(name)
    return tuple(dict.fromkeys(categories))


def _paper_ids(payload: dict[str, Any]) -> tuple[str, ...]:
    results = payload.get("results")
    if not isinstance(results, list):
        return ()
    ids = []
    for item in results:
        if isinstance(item, dict):
            ids.append(str(item.get("id") or "").strip())
    return tuple(ids)


def _repositories_from_pwc_payload(payload: Any) -> tuple[str, ...]:
    candidates: list[Any] = []
    if isinstance(payload, dict):
        results = payload.get("results")
        if isinstance(results, list):
            candidates.extend(results)
        for key in ("repositories", "repository", "code_url", "url", "github_url"):
            value = payload.get(key)
            if isinstance(value, list):
                candidates.extend(value)
            elif value:
                candidates.append(value)
    elif isinstance(payload, list):
        candidates.extend(payload)

    repositories = []
    for item in candidates:
        if isinstance(item, dict):
            values = [item.get(key) for key in ("url", "repository_url", "github_url", "code_url", "full_name")]
        else:
            values = [item]
        for value in values:
            repository = _github_repo_name(str(value or ""))
            if repository:
                repositories.append(repository)
    return tuple(dict.fromkeys(repositories))


def _github_repo_name(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    match = re.search(r"github\.com[:/]+([^/\s]+)/([^/#?\s]+)", text, flags=re.IGNORECASE)
    if match:
        return f"{match.group(1)}/{match.group(2).removesuffix('.git')}"
    if re.fullmatch(r"[^/\s]+/[^/\s]+", text):
        owner, name = text.split("/", 1)
        return f"{owner}/{name.removesuffix('.git')}"
    return ""


def _json_string_field(block: str, key: str) -> str:
    match = re.search(rf'"{re.escape(key)}":"((?:\\.|[^"\\])*)"', block)
    if not match:
        return ""
    return _unescape_json_string(match.group(1))


def _json_array_values(value: str) -> tuple[str, ...]:
    return tuple(_unescape_json_string(item) for item in re.findall(r'"((?:\\.|[^"\\])*)"', value))


def _unescape_json_string(value: str) -> str:
    return (
        value.replace(r"\/", "/")
        .replace(r"\"", '"')
        .replace(r"\n", " ")
        .replace(r"\t", " ")
        .replace(r"\\", "\\")
        .strip()
    )


def _query_match_score(snapshot: PaperSnapshot, query_terms: tuple[str, ...]) -> int:
    if not query_terms:
        return 0
    text = f"{snapshot.title} {snapshot.abstract} {' '.join(snapshot.categories)}".casefold()
    return sum(1 for term in query_terms if term in text)


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PaperError(f"Paper payload must include non-empty {key!r}.")
    return value.strip()


def _str_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _entry_text(entry: ET.Element, path: str, ns: dict[str, str]) -> str:
    value = entry.findtext(path, default="", namespaces=ns)
    if not value.strip():
        raise PaperError(f"arXiv entry missing required field: {path}")
    return value


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _infer_technologies(title: str, abstract: str, categories: tuple[str, ...]) -> tuple[str, ...]:
    text = f"{title} {abstract}".casefold()
    technologies = []
    if "agent" in text:
        technologies.append("AI agents")
    if "retrieval" in text or "rag" in text:
        technologies.append("RAG")
    if "vision-language" in text or "multimodal" in text:
        technologies.append("VLM")
    if "reasoning" in text:
        technologies.append("Reasoning")
    if "cs.ai" in {category.casefold() for category in categories} and "AI research" not in technologies:
        technologies.append("AI research")
    return tuple(technologies)


def _infer_companies(title: str, abstract: str) -> tuple[str, ...]:
    text = f"{title} {abstract}".casefold()
    companies = []
    for name in ("OpenAI", "Anthropic", "Google", "Meta", "NVIDIA", "Apple", "Microsoft"):
        if name.casefold() in text:
            companies.append(name)
    return tuple(companies)
