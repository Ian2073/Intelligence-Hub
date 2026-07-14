from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_ALLOWED = {
    "identity": "identity.md",
    "decision_framework": "decision_framework.md",
    "signal_compression": "signal_compression.md",
    "mission": "mission.md",
    "values": "values.md",
}


@dataclass(frozen=True)
class KnowledgeSnippet:
    key: str
    path: Path
    content: str


@dataclass(frozen=True)
class KnowledgeLoadResult:
    snippets: tuple[KnowledgeSnippet, ...]
    truncated: bool

    @property
    def used_keys(self) -> tuple[str, ...]:
        return tuple(snippet.key for snippet in self.snippets)

    def render_context(self) -> str:
        return "\n\n".join(f"--- knowledge:{snippet.key} ---\n{snippet.content}" for snippet in self.snippets)


def load_knowledge_context(
    knowledge_dir: Path,
    *,
    keys: tuple[str, ...],
    char_limit: int = 6000,
    allowed: dict[str, str] | None = None,
) -> KnowledgeLoadResult:
    base = knowledge_dir.resolve()
    allowed_map = allowed or DEFAULT_ALLOWED
    snippets: list[KnowledgeSnippet] = []
    used_chars = 0
    truncated = False
    for key in keys:
        if key not in allowed_map:
            raise ValueError(f"Knowledge key is not allowed: {key}")
        path = (base / allowed_map[key]).resolve()
        if base not in path.parents and path != base:
            raise ValueError(f"Knowledge path escapes knowledge directory: {path}")
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8").strip()
        remaining = char_limit - used_chars
        if remaining <= 0:
            truncated = True
            break
        if len(content) > remaining:
            content = content[:remaining].rstrip()
            truncated = True
        snippets.append(KnowledgeSnippet(key=key, path=path, content=content))
        used_chars += len(content)
    return KnowledgeLoadResult(snippets=tuple(snippets), truncated=truncated)
