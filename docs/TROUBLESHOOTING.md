# Troubleshooting

## `hermes demo` Fails

Run the demo from the repository root after installing dependencies:

```powershell
.\hub_env\Scripts\python.exe -m hermes demo --date 2026-07-10 --output examples/output/obsidian
```

Common causes:

- dependencies were installed into a different Python environment
- fixture files under `data/fixtures/` are missing
- the command is not running from the repository root
- Python is older than 3.11

Use `.\hub_env\Scripts\python.exe -m hermes doctor --profile demo` to check the zero-secret demo prerequisites.

## Do I Need Notion Or A Cloud API Key?

No. The fixture demo does not require Notion, Telegram, GitHub credentials, or cloud LLM keys. Optional integrations are only needed for production or live checks.

## `main.py` vs `hermes demo`

Use `python -m hermes demo` for the public first-run path. `main.py` remains the production orchestration entrypoint and may use production-oriented settings.

## Windows vs Linux Commands

Windows:

```powershell
.\hub_env\Scripts\python.exe -m hermes demo --date 2026-07-10 --output examples/output/obsidian
```

Linux/macOS:

```bash
python -m hermes demo --date 2026-07-10 --output examples/output/obsidian
```

## `HERMES_MEMORY_DB` And Production Memory

Production memory defaults to `data/hermes_memory.sqlite` and is ignored by Git. For dry-runs, use an isolated path or the demo command, which writes a demo database under the output directory.

## `--model-synthesis`

Fixture runs and CI use deterministic fallback output by default. `--model-synthesis` is for production-quality synthesis and may call the configured pro-tier cloud model when enabled.

## Notion Provisioning Errors

Check:

- `NOTION_TOKEN`
- `NOTION_PARENT_PAGE_ID`
- database ids in `.env`
- whether the integration has access to the parent page

Run live checks only after credentials are configured:

```powershell
.\hub_env\Scripts\python.exe -m hermes doctor --live
```

## GitHub Rate Limits

The demo uses fixtures and does not call GitHub. Live GitHub checks can run unauthenticated, but production should configure `GITHUB_TOKEN` to avoid low rate limits.

## Doctor Shows Many `SKIPPED` Checks

Skipped optional integrations are expected in demo mode. Use:

```powershell
.\hub_env\Scripts\python.exe -m hermes doctor --profile demo
```

for demo readiness, and use the default or live doctor profile for production configuration review.

## Reproduce CI Locally

```powershell
.\hub_env\Scripts\python.exe -m pytest tests -q
.\hub_env\Scripts\python.exe -m compileall contracts core connectors hermes workflows scripts main.py
.\hub_env\Scripts\python.exe scripts\smoke_test.py
.\hub_env\Scripts\python.exe scripts\acceptance_check.py
.\hub_env\Scripts\python.exe -m hermes demo --date 2026-07-10 --output examples/output/obsidian
.\hub_env\Scripts\python.exe scripts\first_run_check.py
```
