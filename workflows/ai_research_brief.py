from __future__ import annotations

from core.docs_loader import ProjectDoc, build_docs_context
from core.model_router import ModelRouter
from core.model_policy import tier_for_task
from core.sources import SourceRecord, build_source_context


def generate_ai_research_brief(
    soul: list[ProjectDoc],
    workflow_prompt: ProjectDoc,
    router: ModelRouter,
    topic: str,
    source_records: list[SourceRecord] | None = None,
) -> str:
    prompt = build_prompt(soul, workflow_prompt, topic, source_records or [])
    return router.generate(prompt, tier=tier_for_task("research_brief")).strip()


def build_prompt(
    soul: list[ProjectDoc],
    workflow_prompt: ProjectDoc,
    topic: str,
    source_records: list[SourceRecord] | None = None,
) -> str:
    soul_context = build_docs_context(soul)
    source_context = build_source_context(source_records or [])
    return f"""You are Hermes, a local-first intelligence hub.

Use the Hermes soul below as system/context memory. Use the workflow prompt as task instructions.
The runtime topic and structured source items are the primary subject. Do not let Hermes architecture or local project docs dominate the brief.
If structured source items are provided, ground the brief in those items and do not invent additional sources.

Hermes soul:
{soul_context}

Workflow prompt:
{workflow_prompt.content}

Runtime topic:
{topic}

Structured source items:
{source_context}
"""
