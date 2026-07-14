from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from connectors.retry import retry_on_transient


class GitHubError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitHubUserInfo:
    login: str
    id: int


@dataclass(frozen=True)
class GitHubRepoSnapshot:
    owner: str
    name: str
    full_name: str
    url: str
    description: str
    language: str
    stars: int
    open_issues: int
    topics: tuple[str, ...]
    pushed_at: str
    updated_at: str
    default_branch: str
    observed_at: str
    latest_release: str
    latest_release_url: str
    latest_release_published_at: str
    latest_pull_request: str
    latest_pull_request_url: str
    latest_pull_request_updated_at: str
    latest_issue: str
    latest_issue_url: str
    latest_issue_updated_at: str
    contributor_count: int


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        base_url: str = "https://api.github.com",
        timeout: float = 30.0,
    ) -> None:
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_authenticated_user(self) -> GitHubUserInfo:
        user_data = self._get_json("/user")
        if user_data is None:
            raise GitHubError("GitHub did not return authenticated user identity.")
        login = str(user_data.get("login") or "").strip()
        user_id = user_data.get("id")
        if not login or not isinstance(user_id, int):
            raise GitHubError("GitHub did not return authenticated user identity.")
        return GitHubUserInfo(login=login, id=user_id)

    def fetch_repository(self, owner: str, name: str, observed_at: str) -> GitHubRepoSnapshot:
        repo_data = self._get_json(f"/repos/{owner}/{name}")
        release_data = self._get_json(f"/repos/{owner}/{name}/releases/latest", allow_404=True)
        pull_data = self._get_list(f"/repos/{owner}/{name}/pulls?state=all&sort=updated&direction=desc&per_page=1")
        issue_data = self._get_list(f"/repos/{owner}/{name}/issues?state=all&sort=updated&direction=desc&per_page=5")
        contributor_data = self._get_list(f"/repos/{owner}/{name}/contributors?per_page=100", allow_404=True)
        return parse_repository_snapshot(repo_data, release_data, observed_at, pull_data, issue_data, contributor_data)

    def _get_json(self, path: str, allow_404: bool = False) -> dict[str, Any] | None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = retry_on_transient(
                lambda: httpx.get(f"{self.base_url}{path}", headers=headers, timeout=self.timeout, follow_redirects=True),
                operation_name="GitHub API",
            )
        except Exception as exc:
            raise GitHubError(f"GitHub request failed: {exc}") from exc

        if allow_404 and response.status_code == 404:
            return None
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubError(
                f"GitHub returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc

        data = response.json()
        if not isinstance(data, dict):
            raise GitHubError("GitHub returned a non-object payload.")
        return data

    def _get_list(self, path: str, allow_404: bool = False) -> list[dict[str, Any]]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = retry_on_transient(
                lambda: httpx.get(f"{self.base_url}{path}", headers=headers, timeout=self.timeout, follow_redirects=True),
                operation_name="GitHub API",
            )
        except Exception as exc:
            raise GitHubError(f"GitHub request failed: {exc}") from exc

        if allow_404 and response.status_code == 404:
            return []
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubError(
                f"GitHub returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc

        data = response.json()
        if not isinstance(data, list):
            raise GitHubError("GitHub returned a non-list payload.")
        return [item for item in data if isinstance(item, dict)]


def parse_repository_snapshot(
    repo_data: dict[str, Any],
    release_data: dict[str, Any] | None,
    observed_at: str,
    pull_data: list[dict[str, Any]] | None = None,
    issue_data: list[dict[str, Any]] | None = None,
    contributor_data: list[dict[str, Any]] | None = None,
) -> GitHubRepoSnapshot:
    full_name = _required_str(repo_data, "full_name")
    owner_data = repo_data.get("owner")
    owner = ""
    if isinstance(owner_data, dict):
        owner = str(owner_data.get("login", "")).strip()
    if not owner and "/" in full_name:
        owner = full_name.split("/", 1)[0]

    latest_release = ""
    latest_release_url = ""
    latest_release_published_at = ""
    if release_data:
        latest_release = str(release_data.get("tag_name") or release_data.get("name") or "").strip()
        latest_release_url = str(release_data.get("html_url") or "").strip()
        latest_release_published_at = str(release_data.get("published_at") or "").strip()

    latest_pr = _first_item(pull_data or ())
    latest_issue_item = _first_non_pull_request_issue(issue_data or ())
    latest_pull_request = str(latest_pr.get("title") or "").strip() if latest_pr else ""
    latest_pull_request_url = str(latest_pr.get("html_url") or "").strip() if latest_pr else ""
    latest_pull_request_updated_at = str(latest_pr.get("updated_at") or "").strip() if latest_pr else ""
    latest_issue = str(latest_issue_item.get("title") or "").strip() if latest_issue_item else ""
    latest_issue_url = str(latest_issue_item.get("html_url") or "").strip() if latest_issue_item else ""
    latest_issue_updated_at = str(latest_issue_item.get("updated_at") or "").strip() if latest_issue_item else ""

    return GitHubRepoSnapshot(
        owner=owner,
        name=_required_str(repo_data, "name"),
        full_name=full_name,
        url=_required_str(repo_data, "html_url"),
        description=str(repo_data.get("description") or "").strip(),
        language=str(repo_data.get("language") or "").strip(),
        stars=_int(repo_data, "stargazers_count"),
        open_issues=_int(repo_data, "open_issues_count"),
        topics=_str_tuple(repo_data.get("topics")),
        pushed_at=str(repo_data.get("pushed_at") or "").strip(),
        updated_at=str(repo_data.get("updated_at") or "").strip(),
        default_branch=str(repo_data.get("default_branch") or "").strip(),
        observed_at=observed_at.strip(),
        latest_release=latest_release,
        latest_release_url=latest_release_url,
        latest_release_published_at=latest_release_published_at,
        latest_pull_request=latest_pull_request,
        latest_pull_request_url=latest_pull_request_url,
        latest_pull_request_updated_at=latest_pull_request_updated_at,
        latest_issue=latest_issue,
        latest_issue_url=latest_issue_url,
        latest_issue_updated_at=latest_issue_updated_at,
        contributor_count=len(contributor_data or ()),
    )


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GitHubError(f"GitHub payload must include non-empty {key!r}.")
    return value.strip()


def _int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or value < 0:
        raise GitHubError(f"GitHub payload must include non-negative integer {key!r}.")
    return value


def _str_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _first_item(items: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> dict[str, Any]:
    return items[0] if items else {}


def _first_non_pull_request_issue(items: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> dict[str, Any]:
    for item in items:
        if "pull_request" not in item:
            return item
    return {}
