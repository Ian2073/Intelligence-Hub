from __future__ import annotations

from connectors.papers import PapersWithCodeClient, parse_arxiv_feed, parse_paper_snapshot, parse_papers_with_code_response
from core.memory import MemoryStore
from core.paper_radar import ingest_paper_snapshot


def test_parse_paper_snapshot_preserves_relationship_hints() -> None:
    snapshot = parse_paper_snapshot(
        {
            "title": "Agentic Retrieval for Code Editing",
            "url": "https://arxiv.org/abs/2607.00001",
            "published_at": "2026-07-01",
            "authors": ["A. Researcher"],
            "abstract": "A paper about agentic retrieval for code editing.",
            "categories": ["cs.AI"],
            "technologies": ["AI agents", "RAG"],
            "repositories": ["All-Hands-AI/OpenHands"],
            "companies": ["Anthropic"],
        },
        "2026-07-02",
    )

    assert snapshot.title == "Agentic Retrieval for Code Editing"
    assert snapshot.technologies == ("AI agents", "RAG")
    assert snapshot.repositories == ("All-Hands-AI/OpenHands",)
    assert snapshot.companies == ("Anthropic",)


def test_parse_arxiv_feed_maps_atom_entries_to_paper_snapshots() -> None:
    feed = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>https://arxiv.org/abs/2607.00001</id>
        <updated>2026-07-01T00:00:00Z</updated>
        <published>2026-07-01T00:00:00Z</published>
        <title>Agentic Retrieval for Code Editing</title>
        <summary>We study agentic retrieval augmented generation for code editing.</summary>
        <author><name>A. Researcher</name></author>
        <category term="cs.AI" />
      </entry>
    </feed>
    """

    snapshots = parse_arxiv_feed(feed, observed_at="2026-07-02")

    assert len(snapshots) == 1
    assert snapshots[0].title == "Agentic Retrieval for Code Editing"
    assert snapshots[0].url == "https://arxiv.org/abs/2607.00001"
    assert snapshots[0].technologies == ("AI agents", "RAG", "AI research")
    assert snapshots[0].categories == ("cs.AI",)


def test_parse_papers_with_code_response_maps_repositories_and_tasks() -> None:
    payload = {
        "results": [
            {
                "id": "agentic-retrieval-for-code-editing",
                "title": "Agentic Retrieval for Code Editing",
                "abstract": "We study agentic retrieval augmented generation for code editing agents.",
                "url_abs": "https://arxiv.org/abs/2607.00001",
                "published": "2026-07-01",
                "authors": [{"name": "A. Researcher"}],
                "tasks": [{"name": "Code Editing"}],
                "repositories": [
                    {"url": "https://github.com/All-Hands-AI/OpenHands"},
                    {"url": "https://github.com/All-Hands-AI/OpenHands.git"},
                ],
            }
        ]
    }

    snapshots = parse_papers_with_code_response(payload, observed_at="2026-07-02")

    assert len(snapshots) == 1
    assert snapshots[0].title == "Agentic Retrieval for Code Editing"
    assert snapshots[0].authors == ("A. Researcher",)
    assert snapshots[0].categories == ("Code Editing",)
    assert snapshots[0].repositories == ("All-Hands-AI/OpenHands",)
    assert snapshots[0].technologies == ("AI agents", "RAG")


def test_parse_huggingface_papers_page_maps_embedded_records() -> None:
    from connectors.papers import parse_huggingface_papers_page

    html = (
        '{&quot;id&quot;:&quot;2607.00001&quot;,&quot;authors&quot;:[{&quot;name&quot;:&quot;A. Researcher&quot;,&quot;hidden&quot;:false}],'
        '&quot;publishedAt&quot;:&quot;2026-07-01T00:00:00.000Z&quot;,&quot;title&quot;:&quot;Agentic Retrieval for Code Editing&quot;,'
        '&quot;summary&quot;:&quot;Agentic retrieval augmented generation for code editing agents.&quot;,'
        '&quot;githubRepo&quot;:&quot;https://github.com/All-Hands-AI/OpenHands&quot;,'
        '&quot;ai_keywords&quot;:[&quot;agent&quot;,&quot;retrieval&quot;]}'
    )

    snapshots = parse_huggingface_papers_page(html, observed_at="2026-07-02")

    assert len(snapshots) == 1
    assert snapshots[0].url == "https://arxiv.org/abs/2607.00001"
    assert snapshots[0].published_at == "2026-07-01"
    assert snapshots[0].authors == ("A. Researcher",)
    assert snapshots[0].repositories == ("All-Hands-AI/OpenHands",)
    assert snapshots[0].technologies == ("AI agents", "RAG")


def test_papers_with_code_client_enriches_papers_with_repository_endpoint(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, payload, status_code=200, headers=None, text="ok"):
            self._payload = payload
            self.status_code = status_code
            self.headers = headers or {}
            self.text = text

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    calls = []

    def fake_get(url, timeout, **kwargs):
        calls.append((url, timeout))
        if url.startswith("https://pwc.example/api/v1/papers/?"):
            return FakeResponse(
                {
                    "results": [
                        {
                            "id": "agentic-retrieval-for-code-editing",
                            "title": "Agentic Retrieval for Code Editing",
                            "abstract": "Agentic retrieval augmented generation for code editing.",
                            "url_abs": "https://arxiv.org/abs/2607.00001",
                            "published": "2026-07-01",
                        }
                    ]
                }
            )
        return FakeResponse(
            {
                "results": [
                    {"url": "https://github.com/All-Hands-AI/OpenHands"},
                ]
            }
        )

    monkeypatch.setattr("connectors.papers.httpx.get", fake_get)

    client = PapersWithCodeClient(base_url="https://pwc.example/api/v1", timeout=9.0)
    snapshots = client.search("agentic code editing", observed_at="2026-07-02", max_results=1)

    assert len(calls) == 2
    assert snapshots[0].repositories == ("All-Hands-AI/OpenHands",)
    assert snapshots[0].technologies == ("AI agents", "RAG")


def test_papers_with_code_client_falls_back_to_huggingface_redirect(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, payload=None, status_code=200, headers=None, text="ok"):
            self._payload = payload or {}
            self.status_code = status_code
            self.headers = headers or {}
            self.text = text

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    calls = []
    hf_html = (
        '{&quot;id&quot;:&quot;2607.00001&quot;,&quot;authors&quot;:[{&quot;name&quot;:&quot;A. Researcher&quot;,&quot;hidden&quot;:false}],'
        '&quot;publishedAt&quot;:&quot;2026-07-01T00:00:00.000Z&quot;,&quot;title&quot;:&quot;Agentic Retrieval for Code Editing&quot;,'
        '&quot;summary&quot;:&quot;Agentic retrieval augmented generation for code editing agents.&quot;,'
        '&quot;githubRepo&quot;:&quot;https://github.com/All-Hands-AI/OpenHands&quot;}'
    )

    def fake_get(url, timeout, **kwargs):
        calls.append((url, kwargs))
        if url.startswith("https://pwc.example/api/v1/papers/?"):
            return FakeResponse(status_code=302, headers={"location": "https://huggingface.co/papers/trending"})
        return FakeResponse(text=hf_html)

    monkeypatch.setattr("connectors.papers.httpx.get", fake_get)

    client = PapersWithCodeClient(
        base_url="https://pwc.example/api/v1",
        fallback_url="https://huggingface.co/papers/trending",
    )
    snapshots = client.search("agentic code editing", observed_at="2026-07-02", max_results=1)

    assert calls[0][1]["follow_redirects"] is False
    assert len(calls) == 2
    assert snapshots[0].repositories == ("All-Hands-AI/OpenHands",)


def test_ingest_paper_snapshot_links_paper_to_radar_entities(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        snapshot = parse_paper_snapshot(
            {
                "title": "Agentic Retrieval for Code Editing",
                "url": "https://arxiv.org/abs/2607.00001",
                "published_at": "2026-07-01",
                "authors": ["A. Researcher"],
                "abstract": "A paper about agentic retrieval for code editing.",
                "categories": ["cs.AI"],
                "technologies": ["AI agents", "RAG"],
                "repositories": ["All-Hands-AI/OpenHands"],
                "companies": ["Anthropic"],
            },
            "2026-07-02",
        )

        result = ingest_paper_snapshot(store, snapshot, revisit_date="2026-07-09")

        assert result.entity.kind == "paper"
        assert len(result.relationships) == 4
        assert result.decision.action == "Prototype"
        assert result.brief_line.startswith("Prototype: Agentic Retrieval for Code Editing connects to 4 radar entities.")
        assert "下一步：檢查 All-Hands-AI/OpenHands 是否能做最小驗證。" in result.brief_line
        assert "Why now:" in result.decision.rationale
        assert "What changed:" in result.decision.rationale
        assert "Connects to:" in result.decision.rationale
        assert "What to do:" in result.decision.rationale
        assert "Confidence:" in result.decision.rationale
    finally:
        store.close()
