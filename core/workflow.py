from __future__ import annotations

from dataclasses import dataclass

from core.docs_loader import ProjectDoc
from core.model_router import ModelRouter
from core.sources import SourceRecord
from workflows.ai_research_brief import generate_ai_research_brief


@dataclass(frozen=True)
class WorkflowResult:
    title: str
    body: str


def run_ai_research_brief(
    soul: list[ProjectDoc],
    workflow_prompt: ProjectDoc,
    router: ModelRouter,
    topic: str,
    source_records: list[SourceRecord] | None = None,
) -> WorkflowResult:
    body = generate_ai_research_brief(
        soul=soul,
        workflow_prompt=workflow_prompt,
        router=router,
        topic=topic,
        source_records=source_records or [],
    )
    return WorkflowResult(title=f"Intelligence Hub AI Research Brief: {topic}", body=body)
