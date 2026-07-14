from __future__ import annotations

import json

import pytest

from core.watchlist import load_domain_watchlist, load_github_watchlist, load_paper_watchlist


def test_load_github_watchlist_accepts_repo_shorthand(tmp_path) -> None:
    path = tmp_path / "watchlist.json"
    path.write_text(
        json.dumps(
            [
                {
                    "repo": "All-Hands-AI/OpenHands",
                    "fixture": "github/All-Hands-AI_OpenHands.json",
                }
            ]
        ),
        encoding="utf-8",
    )

    items = load_github_watchlist(path)

    assert len(items) == 1
    assert items[0].owner == "All-Hands-AI"
    assert items[0].name == "OpenHands"
    assert items[0].full_name == "All-Hands-AI/OpenHands"


def test_load_github_watchlist_rejects_missing_repo_identity(tmp_path) -> None:
    path = tmp_path / "watchlist.json"
    path.write_text(json.dumps([{"fixture": "x.json"}]), encoding="utf-8")

    with pytest.raises(ValueError, match="must include owner/name or repo"):
        load_github_watchlist(path)


def test_load_paper_watchlist_requires_title_and_fixture(tmp_path) -> None:
    path = tmp_path / "papers.json"
    path.write_text(
        json.dumps(
            [
                {
                    "title": "Agentic Retrieval for Code Editing",
                    "fixture": "papers/agentic_retrieval_for_code_editing.json",
                    "query": "all:agentic",
                    "max_results": 3,
                }
            ]
        ),
        encoding="utf-8",
    )

    items = load_paper_watchlist(path)

    assert len(items) == 1
    assert items[0].title == "Agentic Retrieval for Code Editing"
    assert items[0].fixture == "papers/agentic_retrieval_for_code_editing.json"
    assert items[0].query == "all:agentic"
    assert items[0].max_results == 3


def test_load_paper_watchlist_accepts_query_only_for_live_fetch(tmp_path) -> None:
    path = tmp_path / "papers.json"
    path.write_text(
        json.dumps(
            [
                {
                    "title": "Agent papers",
                    "query": "all:agent",
                }
            ]
        ),
        encoding="utf-8",
    )

    items = load_paper_watchlist(path)

    assert items[0].fixture == ""
    assert items[0].query == "all:agent"
    assert items[0].max_results == 5


def test_load_domain_watchlist_requires_domain_name_and_fixture(tmp_path) -> None:
    path = tmp_path / "domains.json"
    path.write_text(
        json.dumps(
            [
                {
                    "domain": "Startup Intelligence",
                    "name": "AI developer tool consolidation",
                    "fixture": "domains/startup_ai_developer_tool_consolidation.json",
                }
            ]
        ),
        encoding="utf-8",
    )

    items = load_domain_watchlist(path)

    assert len(items) == 1
    assert items[0].domain == "Startup Intelligence"
    assert items[0].fixture == "domains/startup_ai_developer_tool_consolidation.json"


def test_load_domain_watchlist_accepts_rss_source_without_fixture(tmp_path) -> None:
    path = tmp_path / "domains.json"
    path.write_text(
        json.dumps(
            [
                {
                    "domain": "NVIDIA Intelligence",
                    "name": "Inference platform moat",
                    "rss_url": "https://blogs.nvidia.com/feed/",
                    "max_results": 2,
                }
            ]
        ),
        encoding="utf-8",
    )

    items = load_domain_watchlist(path)

    assert len(items) == 1
    assert items[0].fixture == ""
    assert items[0].rss_url == "https://blogs.nvidia.com/feed/"
    assert items[0].max_results == 2
