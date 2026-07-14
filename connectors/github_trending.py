from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import httpx

from connectors.github import GitHubRepoSnapshot, parse_repository_snapshot
from connectors.retry import retry_on_transient


class GitHubTrendingError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitHubTrendingClient:
    token: str | None = None
    base_url: str = "https://api.github.com"
    timeout: float = 30.0

    def fetch_trending(
        self,
        observed_at: str,
        *,
        language: str = "",
        min_stars: int = 100,
        created_within_days: int = 7,
        max_results: int = 10,
    ) -> list[GitHubRepoSnapshot]:
        """Search GitHub for recently created repos with rapid star growth."""
        since = (date.fromisoformat(observed_at) - timedelta(days=created_within_days)).isoformat()
        query_parts = [f"created:>{since}", f"stars:>={min_stars}", "sort:stars"]
        if language:
            query_parts.insert(0, f"language:{language}")
        query = " ".join(query_parts)

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = retry_on_transient(
                lambda: httpx.get(
                    f"{self.base_url}/search/repositories",
                    params={"q": query, "sort": "stars", "order": "desc", "per_page": str(max_results)},
                    headers=headers,
                    timeout=self.timeout,
                ),
                operation_name="GitHub Trending Search",
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubTrendingError(
                f"GitHub search returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except Exception as exc:
            raise GitHubTrendingError(f"GitHub trending search failed: {exc}") from exc

        data = response.json()
        items = data.get("items", [])
        if not isinstance(items, list):
            return []

        snapshots = []
        for item in items[:max_results]:
            if not isinstance(item, dict):
                continue
            try:
                snapshot = parse_repository_snapshot(item, None, observed_at)
                snapshots.append(snapshot)
            except Exception:
                continue
        return snapshots
