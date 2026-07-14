from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_platform_runtime_modules_do_not_import_hermes() -> None:
    offenders = _imports_from(
        (
            PROJECT_ROOT / "core",
            PROJECT_ROOT / "connectors",
            PROJECT_ROOT / "workflows",
            PROJECT_ROOT / "contracts",
        ),
        forbidden_root="hermes",
    )

    assert offenders == []


def test_hermes_may_import_platform_core() -> None:
    imports = _imports_from((PROJECT_ROOT / "hermes",), forbidden_root="core")

    assert imports


def _imports_from(roots: tuple[Path, ...], *, forbidden_root: str) -> list[str]:
    offenders: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if forbidden_root in _imported_roots(node):
                    offenders.append(str(path.relative_to(PROJECT_ROOT)))
                    break
    return sorted(offenders)


def _imported_roots(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name.split(".", 1)[0] for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module.split(".", 1)[0],)
    return ()
