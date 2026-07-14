# Project Organization

This document records the intended shape of the Intelligence Hub repository.

Intelligence Hub is the product and platform. The Platform Runtime owns collection, processing, orchestration, canonical persistence, intelligence generation, decision support, delivery, scheduling, and observability. Hermes is an optional research-agent integration and compatibility entrypoint, not the owner of core platform responsibilities.

## Source Areas

- `core/`: product logic, memory, pipelines, delivery, readiness, scheduling, status checks, and platform-neutral interfaces.
- `contracts/`: shared dataclasses and contracts used across connectors, core, workflows, and scripts.
- `connectors/`: external system adapters and parsers for GitHub, papers, domain RSS, Notion, Telegram, Obsidian, model providers, and retries.
- `workflows/`: domain-level intelligence workflows that combine connector output and core radar logic.
- `hermes/`: compatibility CLI and optional research-agent context. It may import platform modules, but platform modules must not import it.
- `scripts/`: operational, validation, scheduled-run, export, and compatibility entrypoints. The primary CLI is `intelligence-hub`.
- `dashboard/`: static local dashboard served by the platform-neutral FastAPI app.
- `examples/`: zero-secret demo instructions and generated demo output location.
- `tests/`: automated tests and short-lived isolated simulation outputs.

## Product Context

- `docs/`: human-maintained product, architecture, operations, roadmap, and design-rationale documents.
- `hermes/soul/`: optional agent identity and behavioral context.
- `knowledge/`: durable thinking framework and product knowledge intended for agent-readable context.
- `prompts/`: workflow prompt contracts.

## Runtime Data

- `data/watchlists/`: configured radar watchlists.
- `data/fixtures/`: deterministic local fixtures for tests and dry-runs.
- `data/obsidian_vault/`: local presentation output when explicitly configured.
- `data/hermes_memory.sqlite`: local SQLite repository database. It is runtime state, not source. The filename remains for compatibility.
- `data/demo/`: generated release demo SQLite database and Obsidian vault. It is runtime state and ignored by git.
- `logs/`: scheduled and manual run logs.
- `exports/`: memory exports and operational snapshots.

## Generated Test Artifacts

The following paths are generated during capability and regression testing and should not be treated as product source:

- `tests/.capability*/`
- `tests/.simulation/`
- `tests/.tmp*/`
- `.pytest_cache/`
- `.pytest_tmp/`
- `__pycache__/`

These directories are intentionally ignored. Keep a generated artifact only when it is being used as explicit evidence for a current review.

## Verification Baseline

Use these commands after structural or pipeline changes:

```powershell
.\hub_env\Scripts\python.exe -m pytest tests -q
.\hub_env\Scripts\ruff.exe check .
.\hub_env\Scripts\python.exe -m compileall contracts core connectors hermes workflows scripts main.py
.\hub_env\Scripts\python.exe scripts\smoke_test.py
.\hub_env\Scripts\intelligence-hub.exe seed-demo
```

For live capability checks, use isolated state and dry-run delivery:

```powershell
$env:HERMES_MEMORY_DB='tests\.capability_manual\memory.sqlite'
$env:OBSIDIAN_ENABLED='1'
$env:OBSIDIAN_VAULT_PATH='tests\.capability_manual\obsidian'
.\hub_env\Scripts\python.exe scripts\run_daily_intelligence.py --date 2026-07-09 --live-github --live-papers-with-code --live-domain-rss --publish-obsidian --notion-url local://notion/manual-dry-run
```

The daily and orchestration CLIs refuse local dry-runs against `data/hermes_memory.sqlite`. Use an isolated `HERMES_MEMORY_DB` for experiments, or use `--publish-notion` for an intentional production run.

## Dependency Boundaries

Platform modules must not depend on the optional Hermes integration:

- `core/` must not import `hermes`.
- `connectors/` must not import `hermes`.
- `workflows/` must not import `hermes`.
- platform-neutral interface modules must not import `hermes`.

Compatibility modules under `hermes/` may import platform modules. Future optional integrations may import platform interfaces.
