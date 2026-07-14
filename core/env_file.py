from __future__ import annotations

from pathlib import Path


def update_env_values(path: Path, values: dict[str, str]) -> None:
    existing_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = {key: value for key, value in values.items() if value}
    updated_lines: list[str] = []

    for line in existing_lines:
        key = _env_key(line)
        if key and key in remaining:
            updated_lines.append(f"{key}={remaining.pop(key)}")
            continue
        updated_lines.append(line)

    if remaining:
        if updated_lines and updated_lines[-1].strip():
            updated_lines.append("")
        for key, value in remaining.items():
            updated_lines.append(f"{key}={value}")

    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def _env_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key = stripped.split("=", 1)[0].strip()
    return key or None
