from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_settings
from core.docs_loader import load_markdown_docs, load_markdown_file, markdown_summary
from core.model_router import ModelRouter
from core.sources import load_source_records, source_summary
from core.workflow import run_ai_research_brief


class SmokeGenerator:
    def generate(self, prompt: str) -> str:
        if "Hermes soul:" not in prompt:
            raise AssertionError("Prompt did not include Hermes soul context.")
        if "Workflow prompt:" not in prompt:
            raise AssertionError("Prompt did not include workflow prompt.")
        if "Project docs:" in prompt:
            raise AssertionError("Prompt included developer docs context.")
        if "AI agent workflow orchestration" not in prompt:
            raise AssertionError("Prompt did not include the runtime topic.")
        if "Structured source items:" not in prompt:
            raise AssertionError("Prompt did not include structured source records section.")
        if "Source 1:" not in prompt:
            raise AssertionError("Prompt did not include typed source records.")
        return (
            "Title: Smoke Brief\n"
            "Disclaimer: This is source-grounded analysis based on provided source items and local context, not live web research.\n"
            "- The brief focuses on AI agent workflow orchestration.\n"
            "- Hermes loads soul and workflow prompts separately.\n"
            "- Hermes grounds the brief in typed source records.\n"
            "Practical implications for Hermes: the local workflow is wired.\n"
            "One recommended next step: run main.py with Ollama."
        )


def main() -> int:
    settings = load_settings(PROJECT_ROOT)
    soul = load_markdown_docs(PROJECT_ROOT / "hermes" / "soul")
    workflow_prompt = load_markdown_file(PROJECT_ROOT / "prompts" / "ai_research_brief.md")
    source_records = load_source_records(settings.source_file)
    print(markdown_summary("Hermes soul files", soul))
    print(f"Workflow prompt loaded: {workflow_prompt.name}: {len(workflow_prompt.content)} chars")
    print(source_summary(source_records))

    router = ModelRouter(settings, generator=SmokeGenerator())
    result = run_ai_research_brief(
        soul=soul,
        workflow_prompt=workflow_prompt,
        router=router,
        topic="AI agent workflow orchestration",
        source_records=source_records,
    )
    if "Smoke Brief" not in result.body:
        print("Smoke test failed: workflow did not return expected brief text.")
        return 1
    if "not live web research" not in result.body:
        print("Smoke test failed: disclaimer is missing.")
        return 1

    if settings.notion_enabled:
        print("Smoke test: Notion credentials detected, but publishing is not performed by smoke_test.py.")
    else:
        print("Smoke test: Notion publishing skipped because optional credentials are missing.")

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
