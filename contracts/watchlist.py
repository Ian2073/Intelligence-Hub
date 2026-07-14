from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GitHubWatchItem:
    owner: str
    name: str
    fixture: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass(frozen=True)
class PaperWatchItem:
    title: str
    fixture: str
    query: str
    max_results: int


@dataclass(frozen=True)
class DomainWatchItem:
    domain: str
    name: str
    fixture: str
    rss_url: str = ""
    max_results: int = 3

