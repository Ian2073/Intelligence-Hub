from __future__ import annotations

from pathlib import Path


def test_connectors_do_not_import_core_modules() -> None:
    root = Path(__file__).resolve().parents[1] / "connectors"
    offenders = []
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "from core" in text or "import core" in text:
            offenders.append(path.name)
    assert offenders == []
