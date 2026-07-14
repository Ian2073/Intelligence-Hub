from __future__ import annotations

from pathlib import Path

from core.docs_loader import ProjectDoc
from core.source_items import SourceItem
from workflows.ai_research_brief import build_prompt


def _doc(name: str, title: str, content: str) -> ProjectDoc:
    return ProjectDoc(path=Path(name), title=title, content=content)


def test_build_prompt_uses_soul_workflow_prompt_and_runtime_topic() -> None:
    soul = [_doc("identity.md", "Identity", "# Identity\n\nHermes stays concise.")]
    workflow_prompt = _doc(
        "ai_research_brief.md",
        "AI Research Brief Workflow",
        "# AI Research Brief Workflow\n\nRequired disclaimer: not live web research.",
    )

    source_items = [
        SourceItem(
            title="Grounded source",
            source_type="github",
            url="https://example.com/repo",
            published_at="2026-07-01",
            summary="A source-grounded item.",
            evidence="Observed in test fixture.",
            tags=("agent",),
            importance=80,
            impact=75,
            momentum=70,
            engineering_value=85,
            adoption=60,
            longevity=72,
            novelty=50,
        )
    ]

    prompt = build_prompt(soul, workflow_prompt, "AI agent workflow orchestration", source_items)

    assert "Hermes soul:" in prompt
    assert "--- identity.md: Identity ---" in prompt
    assert "Workflow prompt:" in prompt
    assert "Required disclaimer: not live web research." in prompt
    assert "Runtime topic:\nAI agent workflow orchestration" in prompt
    assert "Structured source items:" in prompt
    assert "Source 1: Grounded source" in prompt
    assert "Observed in test fixture." in prompt
    assert "Project docs:" not in prompt
