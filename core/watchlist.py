from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contracts.watchlist import DomainWatchItem, GitHubWatchItem, PaperWatchItem


def load_github_watchlist(path: Path) -> list[GitHubWatchItem]:
    resolved = path.resolve()
    if not resolved.exists():
        return []
    raw = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"GitHub watchlist must contain a JSON array: {resolved}")
    return [_parse_item(entry, resolved, index) for index, entry in enumerate(raw)]


def load_paper_watchlist(path: Path) -> list[PaperWatchItem]:
    resolved = path.resolve()
    if not resolved.exists():
        return []
    raw = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Paper watchlist must contain a JSON array: {resolved}")
    return [_parse_paper_item(entry, resolved, index) for index, entry in enumerate(raw)]


def load_domain_watchlist(path: Path) -> list[DomainWatchItem]:
    resolved = path.resolve()
    if not resolved.exists():
        return []
    raw = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Domain watchlist must contain a JSON array: {resolved}")
    return [_parse_domain_item(entry, resolved, index) for index, entry in enumerate(raw)]


def _parse_item(entry: Any, path: Path, index: int) -> GitHubWatchItem:
    if not isinstance(entry, dict):
        raise ValueError(f"GitHub watchlist item #{index + 1} in {path} must be an object.")

    owner = str(entry.get("owner") or "").strip()
    name = str(entry.get("name") or "").strip()
    repo = str(entry.get("repo") or "").strip()
    if repo and (not owner or not name):
        parts = repo.split("/", 1)
        if len(parts) == 2:
            owner, name = parts[0].strip(), parts[1].strip()
    if not owner or not name:
        raise ValueError(f"GitHub watchlist item #{index + 1} in {path} must include owner/name or repo.")

    fixture = str(entry.get("fixture") or "").strip()
    return GitHubWatchItem(owner=owner, name=name, fixture=fixture)


def _parse_paper_item(entry: Any, path: Path, index: int) -> PaperWatchItem:
    if not isinstance(entry, dict):
        raise ValueError(f"Paper watchlist item #{index + 1} in {path} must be an object.")
    title = str(entry.get("title") or "").strip()
    fixture = str(entry.get("fixture") or "").strip()
    query = str(entry.get("query") or "").strip()
    if not title:
        raise ValueError(f"Paper watchlist item #{index + 1} in {path} must include title.")
    if not fixture and not query:
        raise ValueError(f"Paper watchlist item #{index + 1} in {path} must include fixture or query.")
    max_results = entry.get("max_results", 5)
    if not isinstance(max_results, int) or max_results < 1:
        raise ValueError(f"Paper watchlist item #{index + 1} in {path} must include positive integer max_results.")
    return PaperWatchItem(title=title, fixture=fixture, query=query, max_results=max_results)


def _parse_domain_item(entry: Any, path: Path, index: int) -> DomainWatchItem:
    if not isinstance(entry, dict):
        raise ValueError(f"Domain watchlist item #{index + 1} in {path} must be an object.")
    domain = str(entry.get("domain") or "").strip()
    name = str(entry.get("name") or "").strip()
    fixture = str(entry.get("fixture") or "").strip()
    rss_url = str(entry.get("rss_url") or "").strip()
    if not domain:
        raise ValueError(f"Domain watchlist item #{index + 1} in {path} must include domain.")
    if not name:
        raise ValueError(f"Domain watchlist item #{index + 1} in {path} must include name.")
    if not fixture and not rss_url:
        raise ValueError(f"Domain watchlist item #{index + 1} in {path} must include fixture or rss_url.")
    max_results = entry.get("max_results", 3)
    if not isinstance(max_results, int) or max_results < 1:
        raise ValueError(f"Domain watchlist item #{index + 1} in {path} must include positive integer max_results.")
    return DomainWatchItem(domain=domain, name=name, fixture=fixture, rss_url=rss_url, max_results=max_results)
