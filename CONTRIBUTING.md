# Contributing

Intelligence Hub is local-first, fixture-testable, and explicit about the boundary between proposed and canonical knowledge.

## Requirements

- Python 3.11
- Git
- No external services for the default test and demo paths

## Setup

Windows PowerShell:

```powershell
python -m venv hub_env
.\hub_env\Scripts\python.exe -m pip install -e ".[test]"
Copy-Item .env.example .env
```

Linux/macOS:

```bash
python3.11 -m venv hub_env
source hub_env/bin/activate
python -m pip install -e ".[test]"
cp .env.example .env
```

## Required Verification

```bash
ruff check .
python -m pytest tests -q
python -m compileall contracts core connectors hermes workflows scripts main.py
python scripts/smoke_test.py
python scripts/acceptance_check.py
python scripts/first_run_check.py
python scripts/pre_publish_audit.py
```

Run `intelligence-hub seed-demo` twice when changing repository, proposal, decision, or demo behavior. The second run must not create duplicate canonical records.

## Development Principles

- Prefer deterministic fixture tests before live integrations.
- Preserve source evidence and provenance.
- Non-deterministic model or agent output must enter the Proposal Trust Layer before canonical persistence.
- Do not add direct canonical writes that bypass proposal validation.
- Keep core platform modules independent from `hermes`.
- Preserve documented legacy entrypoints without making Hermes the platform owner.
- Avoid unrelated formatting or architecture changes in focused pull requests.

## Public and Private History

The public repository began as a reviewed release snapshot after private incubation. New public work uses normal incremental commits.

Do not merge, force-push, or expose private archive history in the public repository. Public changes may be cherry-picked into the private archive; private history must never be pushed in the opposite direction.

## Security and Fixtures

- Never commit `.env`, credentials, tokens, private IDs, local databases, generated Vaults, logs, caches, or personal paths.
- Use placeholders that cannot be mistaken for real credentials.
- Keep demo fixtures synthetic, deterministic, and connected enough to demonstrate the evidence-to-decision lifecycle.
- Live checks are optional and must not run in default CI.

## Pull Requests

- Explain the user problem and the boundary being changed.
- Include focused tests for behavior changes.
- State whether validation was fixture-only or included live external services.
- Update public documentation when CLI, API, configuration, or output contracts change.
- Confirm `git diff --check`, ruff, tests, compileall, and pre-publish audit.
- Do not claim PostgreSQL, authentication, multi-user hosting, causal reasoning, or other roadmap work unless it is implemented and verified.
