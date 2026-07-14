from __future__ import annotations

from connectors.github import GitHubClient, parse_repository_snapshot
from core.github_radar import ingest_repository_snapshot
from core.memory import MemoryStore


def _repo_payload(stars: int) -> dict:
    return {
        "owner": {"login": "All-Hands-AI"},
        "name": "OpenHands",
        "full_name": "All-Hands-AI/OpenHands",
        "html_url": "https://github.com/All-Hands-AI/OpenHands",
        "description": "AI software engineering agent.",
        "language": "Python",
        "stargazers_count": stars,
        "open_issues_count": 321,
        "topics": ["ai-agent", "developer-tools"],
        "pushed_at": "2026-07-02T00:00:00Z",
        "updated_at": "2026-07-02T00:00:00Z",
        "default_branch": "main",
    }


def test_parse_repository_snapshot_preserves_github_evidence() -> None:
    snapshot = parse_repository_snapshot(
        _repo_payload(25500),
        {
            "tag_name": "v1.2.0",
            "html_url": "https://github.com/All-Hands-AI/OpenHands/releases/tag/v1.2.0",
            "published_at": "2026-07-02T00:00:00Z",
        },
        "2026-07-02",
        [{"title": "Improve browser automation reliability", "html_url": "https://github.com/pr", "updated_at": "2026-07-02"}],
        [{"title": "Agent loop should surface tool permission errors", "html_url": "https://github.com/issue", "updated_at": "2026-07-02"}],
        [{}, {}, {}],
    )

    assert snapshot.full_name == "All-Hands-AI/OpenHands"
    assert snapshot.stars == 25500
    assert snapshot.latest_release == "v1.2.0"
    assert snapshot.latest_pull_request == "Improve browser automation reliability"
    assert snapshot.latest_issue == "Agent loop should surface tool permission errors"
    assert snapshot.contributor_count == 3
    assert snapshot.topics == ("ai-agent", "developer-tools")


def test_ingest_repository_snapshot_updates_existing_entity_and_decides(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        first = parse_repository_snapshot(_repo_payload(24000), None, "2026-07-01")
        first_result = ingest_repository_snapshot(store, first, revisit_date="2026-07-08")

        second = parse_repository_snapshot(
            _repo_payload(25500),
            {
                "tag_name": "v1.2.0",
                "html_url": "https://github.com/All-Hands-AI/OpenHands/releases/tag/v1.2.0",
                "published_at": "2026-07-02T00:00:00Z",
            },
            "2026-07-02",
            [{"title": "Improve browser automation reliability", "html_url": "https://github.com/pr", "updated_at": "2026-07-02"}],
            [{"title": "Agent loop should surface tool permission errors", "html_url": "https://github.com/issue", "updated_at": "2026-07-02"}],
            [{}, {}, {}],
        )
        second_result = ingest_repository_snapshot(store, second, revisit_date="2026-07-09")

        assert second_result.entity.id == first_result.entity.id
        assert second_result.star_delta == 1500
        assert second_result.momentum == "surging"
        assert second_result.decision.action == "Prototype"
        assert "All-Hands-AI/OpenHands has 25500 stars (+1500" in second_result.brief_line

        history = store.get_entity_history(second_result.entity.id)
        assert [item.metric_name for item in history].count("stars") == 2
        assert any(item.metric_name == "latest_release" and item.current_value == "v1.2.0" for item in history)
        assert any(item.metric_name == "latest_pull_request" for item in history)
        assert any(item.metric_name == "latest_issue" for item in history)
        assert any(item.metric_name == "contributors" and item.current_value == "3" for item in history)
        assert "PR: Improve browser automation reliability" in second_result.decision.rationale
        assert "Why now:" in second_result.decision.rationale
        assert "What changed:" in second_result.decision.rationale
        assert "Connects to:" in second_result.decision.rationale
        assert "What to do:" in second_result.decision.rationale
        assert "Confidence:" in second_result.decision.rationale
    finally:
        store.close()


def test_github_client_follows_redirects_for_repository_requests(monkeypatch) -> None:
    calls = []

    class FakeResponse:
        status_code = 200

        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_get(url, *, headers, timeout, follow_redirects):
        calls.append((url, timeout, follow_redirects))
        if url.endswith("/repos/All-Hands-AI/OpenHands"):
            return FakeResponse(_repo_payload(25500))
        if url.endswith("/releases/latest"):
            return FakeResponse({"tag_name": "v1.2.0", "html_url": "https://github.com/release"})
        return FakeResponse([])

    monkeypatch.setattr("connectors.github.httpx.get", fake_get)

    snapshot = GitHubClient(timeout=5).fetch_repository("All-Hands-AI", "OpenHands", "2026-07-02")

    assert snapshot.full_name == "All-Hands-AI/OpenHands"
    assert all(call[2] is True for call in calls)


def test_github_client_get_authenticated_user_uses_token_and_redirects(monkeypatch) -> None:
    calls = []

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"login": "hermes-user", "id": 12345}

    def fake_get(url, *, headers, timeout, follow_redirects):
        calls.append(
            {
                "url": url,
                "authorization": headers.get("Authorization"),
                "timeout": timeout,
                "follow_redirects": follow_redirects,
            }
        )
        return FakeResponse()

    monkeypatch.setattr("connectors.github.httpx.get", fake_get)

    user = GitHubClient(token="ghp-test-token", timeout=7).get_authenticated_user()

    assert user.login == "hermes-user"
    assert user.id == 12345
    assert calls == [
        {
            "url": "https://api.github.com/user",
            "authorization": "Bearer ghp-test-token",
            "timeout": 7,
            "follow_redirects": True,
        }
    ]
