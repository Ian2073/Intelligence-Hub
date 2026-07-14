from __future__ import annotations

from core.config import Settings


def validate_memory_target_for_run(
    settings: Settings,
    *,
    publish_notion: bool,
    notion_url: str,
    operation: str,
) -> str | None:
    """Return a refusal message when a dry-run would write into production memory."""
    default_memory = (settings.project_root / "data" / "hermes_memory.sqlite").resolve()
    if settings.memory_db.resolve() != default_memory:
        return None
    if publish_notion:
        return None
    if not notion_url.strip().lower().startswith("local://"):
        return None
    return (
        f"{operation} refused: dry-run output would write to production memory "
        f"{settings.memory_db}. Set HERMES_MEMORY_DB to an isolated path such as "
        "tests\\.capability_manual\\memory.sqlite, or pass --publish-notion for a production run."
    )
