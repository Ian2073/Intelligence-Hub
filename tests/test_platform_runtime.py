from __future__ import annotations

import ast
from pathlib import Path

from core.platform_runtime import PlatformRuntime
from core.repository import SQLiteRepository
from core.runtime import HermesRuntime


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_platform_runtime_imports_without_hermes_dependency() -> None:
    assert PlatformRuntime.__module__ == "core.platform_runtime"

    tree = ast.parse((PROJECT_ROOT / "core" / "platform_runtime.py").read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert "hermes" not in imported_roots


def test_platform_runtime_runs_fixture_daily_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HERMES_MEMORY_DB", str(tmp_path / "platform.sqlite"))
    runtime = PlatformRuntime.create(PROJECT_ROOT)
    try:
        assert isinstance(runtime.repository, SQLiteRepository)
        result = runtime.run_fixture_daily(
            run_date="2026-07-10",
            output_path=tmp_path / "platform-obsidian",
        )

        assert result.run.title.endswith("2026-07-10")
        assert result.obsidian is not None
        assert result.obsidian.status == "published"
        assert (tmp_path / "platform-obsidian" / "00 Dashboard" / "Home.md").is_file()
        assert list((tmp_path / "platform-obsidian" / "01 Briefs" / "Daily").glob("*.md"))
        assert len(result.run.repository_results) == 12
        assert len(result.run.paper_results) == 6
        assert len(result.run.domain_results) == 5
        assert runtime.memory_status().table_rows["briefs"] == 1
    finally:
        runtime.close()


def test_platform_runtime_uses_deterministic_fallback_when_cloud_key_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HERMES_MEMORY_DB", str(tmp_path / "platform.sqlite"))
    monkeypatch.setenv("HERMES_MODEL_PROVIDER", "cloud")
    monkeypatch.setenv("HERMES_CLOUD_API_KEY", "")
    monkeypatch.setenv("INTELLIGENCE_HUB_CLOUD_API_KEY", "")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    runtime = PlatformRuntime.create(PROJECT_ROOT)
    try:
        assert runtime.model_router() is None
    finally:
        runtime.close()


def test_hermes_runtime_remains_legacy_platform_runtime_name(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HERMES_MEMORY_DB", str(tmp_path / "hermes.sqlite"))
    runtime = HermesRuntime.create(PROJECT_ROOT)
    try:
        assert isinstance(runtime, PlatformRuntime)

        result = runtime.run_fixture_daily(
            run_date="2026-07-10",
            output_path=tmp_path / "hermes-obsidian",
        )

        assert result.obsidian is not None
        assert result.obsidian.status == "published"
        assert (tmp_path / "hermes-obsidian" / "00 Dashboard" / "Home.md").is_file()
        assert list((tmp_path / "hermes-obsidian" / "01 Briefs" / "Daily").glob("*.md"))
    finally:
        runtime.close()


def test_platform_runtime_and_hermes_runtime_fixture_results_are_equivalent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("HERMES_MEMORY_DB", str(tmp_path / "platform.sqlite"))
    platform_runtime = PlatformRuntime.create(PROJECT_ROOT)
    try:
        platform_result = platform_runtime.run_fixture_daily(
            run_date="2026-07-10",
            output_path=tmp_path / "platform-obsidian",
        )
    finally:
        platform_runtime.close()

    monkeypatch.setenv("HERMES_MEMORY_DB", str(tmp_path / "hermes.sqlite"))
    hermes_runtime = HermesRuntime.create(PROJECT_ROOT)
    try:
        hermes_result = hermes_runtime.run_fixture_daily(
            run_date="2026-07-10",
            output_path=tmp_path / "hermes-obsidian",
        )
    finally:
        hermes_runtime.close()

    assert hermes_result.run.title == platform_result.run.title
    assert hermes_result.brief.brief_type == platform_result.brief.brief_type
    assert hermes_result.brief.domain == platform_result.brief.domain
    assert hermes_result.brief.top_actions == platform_result.brief.top_actions
    assert len(hermes_result.run.repository_results) == len(platform_result.run.repository_results)
    assert len(hermes_result.run.paper_results) == len(platform_result.run.paper_results)
    assert len(hermes_result.run.domain_results) == len(platform_result.run.domain_results)
    assert [item.decision.action for item in hermes_result.run.repository_results] == [
        item.decision.action for item in platform_result.run.repository_results
    ]
