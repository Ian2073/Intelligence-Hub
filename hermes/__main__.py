from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from core.config import load_settings
from core.doctor import run_doctor
from core.memory import MemoryStore
from core.operational_status import build_operational_status, render_operational_status
from core.runtime import HermesRuntime
from core.watchlist import load_domain_watchlist, load_github_watchlist, load_paper_watchlist


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    _configure_stdout()
    parser = argparse.ArgumentParser(
        prog="python -m hermes",
        description="Legacy Hermes compatibility CLI for Intelligence Hub.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Check local readiness.")
    doctor_parser.add_argument("--live", action="store_true", help="Verify external APIs.")
    doctor_parser.add_argument("--profile", choices=("default", "demo"), default="default", help="Select readiness profile.")

    status_parser = subparsers.add_parser("status", help="Show memory and operational status.")
    status_parser.add_argument("--as-of", default=date.today().isoformat())
    status_parser.add_argument("--include-future", action="store_true")

    demo_parser = subparsers.add_parser("demo", help="Run a zero-secret fixture demo.")
    demo_parser.add_argument("--date", default=date.today().isoformat())
    demo_parser.add_argument("--output", default="examples/output/obsidian")

    run_parser = subparsers.add_parser("run", help="Run a registered agent.")
    run_parser.add_argument("agent_id", nargs="?", default="ai_intelligence")
    run_parser.add_argument("--date", default=date.today().isoformat())
    run_parser.add_argument("--publish-obsidian", action="store_true")

    subparsers.add_parser("agents", help="List registered agents.")

    args = parser.parse_args(argv)
    if args.command == "doctor":
        return _doctor(live=args.live, profile=args.profile)
    if args.command == "status":
        return _status(as_of=args.as_of, include_future=args.include_future)
    if args.command == "demo":
        return _demo(run_date=args.date, output=Path(args.output))
    if args.command == "run":
        return _run_agent(agent_id=args.agent_id, run_date=args.date, publish_obsidian=args.publish_obsidian)
    if args.command == "agents":
        return _agents()
    parser.error(f"Unsupported command: {args.command}")
    return 2


def _doctor(*, live: bool, profile: str) -> int:
    report = run_doctor(load_settings(PROJECT_ROOT), live=live, profile=profile)  # type: ignore[arg-type]
    for check in report.checks:
        print(f"[{check.status.upper()}] {check.name}: {check.detail}")
    return 0 if report.ok else 1


def _status(*, as_of: str, include_future: bool) -> int:
    settings = load_settings(PROJECT_ROOT)
    store = MemoryStore(settings.memory_db)
    try:
        print(render_operational_status(build_operational_status(settings, store, as_of=as_of, include_future=include_future)))
    finally:
        store.close()
    return 0


def _demo(*, run_date: str, output: Path) -> int:
    output_path = output if output.is_absolute() else PROJECT_ROOT / output
    os.environ.setdefault("HERMES_MEMORY_DB", str((output_path / "demo-memory.sqlite").resolve()))
    runtime = HermesRuntime.create(PROJECT_ROOT)
    try:
        settings = runtime.settings
        result = runtime.agent_registry.get("ai_intelligence").run(
            store=runtime.store,
            watchlist=load_github_watchlist(settings.github_watchlist_file),
            paper_watchlist=load_paper_watchlist(settings.paper_watchlist_file),
            domain_watchlist=load_domain_watchlist(settings.domain_watchlist_file),
            run_date=run_date,
            revisit_date=(date.fromisoformat(run_date) + timedelta(days=7)).isoformat(),
            notion_url="local://notion/demo",
            fixture_root=settings.fixture_root,
            obsidian_client=runtime.obsidian_client(False) or _markdown_obsidian_client(output_path),
            publish_obsidian=True,
        )
    finally:
        runtime.close()
    print(result.run.title)
    print(f"Markdown demo: {result.obsidian.status if result.obsidian else 'missing'} - {result.obsidian.detail if result.obsidian else ''}")
    return 0


def _run_agent(*, agent_id: str, run_date: str, publish_obsidian: bool) -> int:
    runtime = HermesRuntime.create(PROJECT_ROOT)
    try:
        settings = runtime.settings
        result = runtime.agent_registry.get(agent_id).run(
            store=runtime.store,
            watchlist=load_github_watchlist(settings.github_watchlist_file),
            paper_watchlist=load_paper_watchlist(settings.paper_watchlist_file),
            domain_watchlist=load_domain_watchlist(settings.domain_watchlist_file),
            run_date=run_date,
            revisit_date=(date.fromisoformat(run_date) + timedelta(days=7)).isoformat(),
            notion_url="local://notion/run",
            fixture_root=settings.fixture_root,
            model_router=runtime.model_router(),
            obsidian_client=runtime.obsidian_client(publish_obsidian),
            publish_obsidian=publish_obsidian,
        )
    finally:
        runtime.close()
    print(result.run.title)
    print(f"Brief: {result.brief.id}")
    return 0


def _agents() -> int:
    runtime = HermesRuntime.create(PROJECT_ROOT)
    try:
        for agent in runtime.agent_registry.list_agents():
            print(
                f"{agent.agent_id}: domain={agent.domain}; workflow={agent.workflow}; "
                f"ingestors={','.join(agent.ingestor_types)}; publishers={','.join(agent.publishers)}"
            )
    finally:
        runtime.close()
    return 0


def _markdown_obsidian_client(output_path: Path):
    from connectors.obsidian import ObsidianClient

    return ObsidianClient(output_path)


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
