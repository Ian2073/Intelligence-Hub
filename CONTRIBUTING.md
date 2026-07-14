# Contributing

Intelligence Hub should be useful without secrets. Keep fixture tests and deterministic fallbacks working before adding live integrations. See `docs/CONTRIBUTING.md` for the release-candidate validation checklist.

## Setup

```powershell
python -m venv hub_env
.\hub_env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

## Local Verification

```powershell
.\hub_env\Scripts\python.exe -m pytest tests -q
.\hub_env\Scripts\python.exe -m compileall contracts core connectors hermes workflows scripts main.py
.\hub_env\Scripts\python.exe scripts\smoke_test.py
.\hub_env\Scripts\python.exe scripts\acceptance_check.py
.\hub_env\Scripts\python.exe scripts\first_run_check.py
.\hub_env\Scripts\python.exe -m hermes doctor
.\hub_env\Scripts\python.exe -m hermes demo --date 2026-07-10 --output examples/output/obsidian
```

## Live Checks

Live checks are optional and must stay out of default CI. Use `python -m hermes doctor --live` only after `.env` has credentials. Do not require Notion, Telegram, cloud LLM, or production memory for fixture tests.

## Boundaries

- The public first-run paths are `scripts/intelligence_hub.py seed-demo` and the compatibility `python -m hermes demo`.
- Hermes is an optional integration and compatibility layer, not the owner of canonical persistence.
- `contracts/` contains shared dataclasses used by connectors and core.
- `connectors/` must not import `core`.
- `core/` owns engines, memory, runtime, delivery contracts, and orchestration.
- `workflows/` and `scripts/` compose core behavior; they should not duplicate publisher formatting or model policy.
