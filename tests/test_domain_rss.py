from __future__ import annotations

from connectors.domain_rss import DomainRssClient, parse_domain_rss_feed
from core.watchlist import DomainWatchItem


def test_parse_domain_rss_feed_converts_rss_items_to_domain_signals() -> None:
    feed = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <title>AI Feed</title>
        <item>
          <title>NVIDIA inference platform expands for AI agents</title>
          <link>https://example.com/nvidia-inference</link>
          <pubDate>Wed, 01 Jul 2026 00:00:00 GMT</pubDate>
          <description>New GPU inference tooling for agent deployment.</description>
        </item>
      </channel>
    </rss>
    """
    item = DomainWatchItem(
        domain="NVIDIA Intelligence",
        name="Inference platform moat",
        fixture="",
        rss_url="https://example.com/feed.xml",
        max_results=1,
    )

    snapshots = parse_domain_rss_feed(feed, item, "2026-07-02")

    assert len(snapshots) == 1
    assert snapshots[0].domain == "NVIDIA Intelligence"
    assert snapshots[0].entity_name == "Inference platform moat"
    assert snapshots[0].source_url == "https://example.com/nvidia-inference"
    assert "Inference" in snapshots[0].technologies
    assert "NVIDIA" in snapshots[0].companies


def test_domain_rss_multidimensional_score_rewards_actionable_technical_signals() -> None:
    technical_feed = """<?xml version="1.0"?>
    <rss version="2.0"><channel><item>
      <title>OpenAI releases open source agent framework with function calling benchmarks</title>
      <link>https://example.com/agent-framework</link>
      <description>New architecture improves tool use, MCP integrations, and inference workflow benchmarks.</description>
    </item></channel></rss>
    """
    low_value_feed = """<?xml version="1.0"?>
    <rss version="2.0"><channel><item>
      <title>Opinion roundup: AI chatbot predictions for next year</title>
      <link>https://example.com/opinion</link>
      <description>A sponsored recap with broad predictions and no release details.</description>
    </item></channel></rss>
    """
    item = DomainWatchItem(
        domain="AI Intelligence",
        name="Agent platforms",
        fixture="",
        rss_url="https://example.com/feed.xml",
        max_results=1,
    )

    technical = parse_domain_rss_feed(technical_feed, item, "2026-07-02")[0]
    low_value = parse_domain_rss_feed(low_value_feed, item, "2026-07-02")[0]

    assert technical.impact_score > low_value.impact_score
    assert "Function calling" in technical.technologies
    assert "MCP" in technical.technologies
    assert "OpenAI" in technical.companies


def test_parse_domain_rss_feed_supports_atom_entries() -> None:
    feed = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Apple improves on-device local model tools</title>
        <link href="https://example.com/apple-local-models" />
        <updated>2026-07-02T00:00:00Z</updated>
        <summary>Local inference and privacy are core to the developer workflow.</summary>
      </entry>
    </feed>
    """
    item = DomainWatchItem(
        domain="Apple Intelligence",
        name="On-device AI strategy",
        fixture="",
        rss_url="https://example.com/atom.xml",
        max_results=1,
    )

    snapshots = parse_domain_rss_feed(feed, item, "2026-07-02")

    assert snapshots[0].source_url == "https://example.com/apple-local-models"
    assert "Local inference" in snapshots[0].technologies
    assert "Apple" in snapshots[0].companies


def test_domain_rss_client_follows_feed_redirects(monkeypatch) -> None:
    calls = []

    class FakeResponse:
        text = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>AI infrastructure spending rises</title>
              <link>https://example.com/capex</link>
              <description>GPU capex for model training and inference.</description>
            </item>
          </channel>
        </rss>
        """

        def raise_for_status(self):
            return None

    def fake_get(url, *, timeout, follow_redirects):
        calls.append((url, timeout, follow_redirects))
        return FakeResponse()

    monkeypatch.setattr("connectors.domain_rss.httpx.get", fake_get)
    item = DomainWatchItem(
        domain="Finance Intelligence",
        name="AI infrastructure capex",
        fixture="",
        rss_url="https://example.com/feed",
        max_results=1,
    )

    snapshots = DomainRssClient(timeout=5).fetch(item, "2026-07-02")

    assert calls == [("https://example.com/feed", 5, True)]
    assert snapshots[0].source_url == "https://example.com/capex"
