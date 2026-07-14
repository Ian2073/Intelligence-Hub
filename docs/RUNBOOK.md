# Runbook

Commands below assume the repository root. The public first-run path is the installable `intelligence-hub` CLI; `main.py` and `python -m hermes` remain compatibility entrypoints.

Windows PowerShell virtualenv path:

```powershell
.\hub_env\Scripts\python.exe <script-or-module>
```

If `hub_env` is already activated, the shorter `python ...` form is equivalent.

## Quick Start

Windows PowerShell:

```powershell
python -m venv hub_env
.\hub_env\Scripts\Activate.ps1
python -m pip install -e .
.\hub_env\Scripts\intelligence-hub.exe seed-demo
```

Linux/macOS shell:

```bash
python3.11 -m venv hub_env
source hub_env/bin/activate
python -m pip install -e .
intelligence-hub seed-demo
```

`intelligence-hub seed-demo` uses fixtures, writes the managed demo database under `data/demo/`, and rebuilds the Obsidian Vault without API keys.

## Local Commands

Install dependencies:

```powershell
python -m pip install -e .
```

Run production orchestration directly:

```powershell
python main.py
```

Run offline smoke validation:

```powershell
python scripts/smoke_test.py
```

Legacy Hermes compatibility commands:

```powershell
.\hub_env\Scripts\python.exe -m hermes doctor
.\hub_env\Scripts\python.exe -m hermes doctor --profile demo
.\hub_env\Scripts\python.exe -m hermes status
.\hub_env\Scripts\python.exe -m hermes agents
.\hub_env\Scripts\python.exe -m hermes demo --date 2026-07-10 --output examples/output/obsidian
.\hub_env\Scripts\python.exe -m hermes run ai_intelligence --date 2026-07-10 --publish-obsidian
```

Use `intelligence-hub` for public operation. Use legacy commands only for existing automation that has not migrated.

Run local end-to-end acceptance with fixtures and fake publishers:

```powershell
python scripts/acceptance_check.py
.\scripts\acceptance_check.ps1
```

Acceptance check exercises the full local loop: fixture sources, memory, runtime run ledger, daily, weekly, monthly, Executive Dashboard, Radar, Decision Review, Notion publishing boundary, and Telegram notification boundary. It does not call external APIs and does not write to your real Notion or Telegram.

Run the final readiness audit. By default this does not call external APIs, but it does combine local acceptance, production schedule validation, go-live configuration, runtime memory status, latest Notion surfaces, and Telegram outbox status:

```powershell
.\hub_env\Scripts\python.exe scripts\readiness_audit.py --as-of 2026-07-09
.\scripts\readiness_audit.ps1 -AsOf 2026-07-09
```

The readiness audit exits `0` only when every requirement passes. Use `--live` / `-Live` after credentials are configured to include read-only live API checks in the go-live gate.

After installing Windows scheduled tasks, include installed task verification in the same readiness report:

```powershell
.\hub_env\Scripts\python.exe scripts\readiness_audit.py --as-of 2026-07-09 --check-scheduled-tasks
.\scripts\readiness_audit.ps1 -AsOf 2026-07-09 -CheckScheduledTasks
```

For offline review, pass exported `schtasks /Query /FO CSV /V` output with `--scheduled-tasks-from-csv` / `-ScheduledTasksFromCsv`.

Check local readiness without calling external APIs:

```powershell
.\hub_env\Scripts\python.exe -m hermes doctor --profile demo
.\hub_env\Scripts\python.exe scripts\doctor.py
.\scripts\doctor.ps1
```

The demo profile checks only zero-secret demo prerequisites. The default doctor profile also reports optional production integrations as skipped when they are not configured.

Show the current Intelligence Hub operating status from local memory and `.env`:

```powershell
.\hub_env\Scripts\python.exe scripts\hermes_status.py
.\scripts\hermes_status.ps1
```

This report shows the latest recorded run or brief links, Notion/Telegram delivery status, memory counts, missing go-live credentials, and the next commands to run. New pipeline runs write a runtime ledger entry so scheduled execution can be audited separately from the content stored in each brief.

After API credentials are added to `.env`, verify live integrations without creating Notion pages or sending Telegram messages:

```powershell
.\hub_env\Scripts\python.exe scripts\doctor.py --live
.\scripts\doctor.ps1 -Live
```

Live doctor checks GitHub, arXiv, Papers with Code, configured domain RSS feeds, Notion parent/databases, and Telegram bot identity. It does not create Notion pages and does not send Telegram messages.

Before installing production scheduled tasks, run the go-live gate. Unlike `doctor.py`, missing production credentials or database ids are failures:

```powershell
.\hub_env\Scripts\python.exe scripts\go_live_check.py
.\scripts\go_live_check.ps1
```

After credentials are configured, run live go-live verification:

```powershell
.\hub_env\Scripts\python.exe scripts\go_live_check.py --live
.\scripts\go_live_check.ps1 -Live
```

The go-live check verifies cloud model configuration, distinct fast/pro model routing, GitHub token, all Notion database ids, Telegram settings, the full production schedule plan, and optionally live read-only external API access. It does not create Notion pages and does not send Telegram messages.

Configure cloud-first model routing:

```powershell
HERMES_MODEL_PROVIDER=cloud
HERMES_CLOUD_BASE_URL=https://api.openai.com/v1
HERMES_CLOUD_API_KEY=
HERMES_FAST_MODEL=
HERMES_PRO_MODEL=
HERMES_SYNTHESIS_MODE=hybrid
HERMES_PRO_CALL_LIMIT=8
```

Use `HERMES_FAST_MODEL` for cheap classification and cleanup work. Use `HERMES_PRO_MODEL` for decision-heavy synthesis such as research briefs, weekly/monthly reports, dashboards, and decision reviews. These legacy variable names remain supported; production go-live requires the two values to differ so Intelligence Hub can control token cost. Set `HERMES_MODEL_PROVIDER=ollama` only for local fallback or offline experiments.

For migration from older local experiments, Intelligence Hub also accepts these legacy cloud variables when the `HERMES_*` values are absent:

```powershell
DEEPSEEK_BASE_URL=
DEEPSEEK_API_KEY=
API_MODEL_NAME=
```

`HERMES_CLOUD_*`, `HERMES_FAST_MODEL`, and `HERMES_PRO_MODEL` always take precedence. If only `API_MODEL_NAME` is set, Intelligence Hub uses it for both fast and pro tiers during migration, but `go_live_check.py` will keep failing until you split them.

Daily, weekly, monthly, and dashboard pipelines do not call the model by default. Enable model-assisted executive synthesis explicitly:

```powershell
.\scripts\run_daily_intelligence.ps1 -ModelSynthesis
.\scripts\run_weekly_intelligence.ps1 -ModelSynthesis
.\scripts\run_monthly_intelligence.ps1 -ModelSynthesis
.\scripts\run_executive_dashboard.ps1 -ModelSynthesis
.\scripts\run_hermes_orchestration.ps1 -Weekly -Monthly -ModelSynthesis
```

`-ModelSynthesis` uses the pro tier because it affects the final decision surface. Leave it off for low-cost fixture and connector validation runs. `HERMES_SYNTHESIS_MODE=hybrid` is the default production posture: high-value synthesis can use pro tier up to `HERMES_PRO_CALL_LIMIT`, then the run downgrades to deterministic output.

If the configured model call fails during executive synthesis, Intelligence Hub logs the failure and keeps the pipeline moving with the deterministic fallback summary. This protects scheduled runs from transient cloud model failures while preserving the brief record.

Run daily intelligence dry-run with fixture data:

```powershell
$env:HERMES_MEMORY_DB='tests\.capability_manual\memory.sqlite'
.\hub_env\Scripts\python.exe scripts\run_daily_intelligence.py --date 2026-07-09 --notion-url local://notion/dry-run
.\scripts\run_daily_intelligence.ps1 -Date 2026-07-09
```

Direct Python dry-runs must set `HERMES_MEMORY_DB` to an isolated path. The CLI refuses local dry-runs that would write into `data/hermes_memory.sqlite`.

Daily runs process GitHub repositories, papers, and domain signals from:

- `data/watchlists/github_repos.json`
- `data/watchlists/papers.json`
- `data/watchlists/domain_signals.json`

The initial domain signal foundation includes Finance Intelligence, Cybersecurity Intelligence, Apple Intelligence, NVIDIA Intelligence, and Startup Intelligence. Daily runs write local memory to `data/hermes_memory.sqlite` by default. This file is runtime state and is ignored by source control.

Run the ordered orchestration dry-run. This is the recommended automation entrypoint because it runs stages sequentially against one memory store:

```powershell
python scripts/run_hermes_orchestration.py --date 2026-07-10 --weekly --monthly
.\scripts\run_hermes_orchestration.ps1 -Date 2026-07-10 -Weekly -Monthly
```

Run full ordered orchestration with live sources and notifications after `.env` is configured:

```powershell
.\scripts\run_hermes_orchestration.ps1 -LiveGitHub -LivePapers -LiveDomainRss -PublishNotion -SendTelegram -Weekly -Monthly
```

Use Papers with Code instead of arXiv for live paper search when repository enrichment is more important:

```powershell
.\scripts\run_hermes_orchestration.ps1 -LiveGitHub -LivePapersWithCode -LiveDomainRss -PublishNotion -SendTelegram -Weekly -Monthly
```

Run daily intelligence with live GitHub after `GITHUB_TOKEN` is added to `.env`:

```powershell
.\scripts\run_daily_intelligence.ps1 -LiveGitHub
```

Public GitHub repositories can be fetched without `GITHUB_TOKEN` for development and live doctor checks, but production go-live still requires `GITHUB_TOKEN` to avoid low anonymous rate limits.

Intelligence Hub also accepts `GH_TOKEN` as a fallback if `GITHUB_TOKEN` is absent.

Check GitHub token setup and the first configured watchlist repository:

```powershell
python scripts/github_check.py
.\scripts\github_check.ps1
```

Run daily intelligence with live arXiv paper search:

```powershell
.\scripts\run_daily_intelligence.ps1 -LivePapers
```

Run daily intelligence with live Papers with Code paper search:

```powershell
.\scripts\run_daily_intelligence.ps1 -LivePapersWithCode
```

Papers with Code currently redirects to Hugging Face Papers. The paper connector handles this by parsing Hugging Face Papers and preserving GitHub repository links when present.

Run daily intelligence with live domain RSS sources:

```powershell
.\scripts\run_daily_intelligence.ps1 -LiveDomainRss
```

Publish to Notion and send Telegram after the required `.env` values are added:

```powershell
.\scripts\run_daily_intelligence.ps1 -LiveGitHub -LivePapers -LiveDomainRss -PublishNotion -SendTelegram
```

For Telegram, prefer `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Intelligence Hub also accepts `TELEGRAM_TOKEN` or `TG_BOT_TOKEN`, and `TG_CHAT_ID`, as migration aliases.

Configure the remaining go-live credentials without printing secrets:

```powershell
python scripts/configure_credentials.py
.\scripts\configure_credentials.ps1
```

For non-interactive setup, provide temporary process environment variables and use `--from-env` / `-FromEnv`:

```powershell
$env:HERMES_SETUP_GITHUB_TOKEN="..."
$env:HERMES_SETUP_TELEGRAM_BOT_TOKEN="..."
$env:HERMES_SETUP_TELEGRAM_CHAT_ID="..."
$env:HERMES_SETUP_FAST_MODEL="..."
$env:HERMES_SETUP_PRO_MODEL="..."
python scripts/configure_credentials.py --from-env
```

`HERMES_SETUP_FAST_MODEL` and `HERMES_SETUP_PRO_MODEL` write `HERMES_FAST_MODEL` and `HERMES_PRO_MODEL` into `.env`. Set them to different cloud models before go-live.

Check Telegram setup without sending a message:

```powershell
python scripts/telegram_check.py
.\scripts\telegram_check.ps1
```

Send one real test notification after the bot and chat id are configured:

```powershell
python scripts/telegram_check.py --send-test --notion-url https://notion.so/hermes-telegram-check
.\scripts\telegram_check.ps1 -SendTest -NotionUrl https://notion.so/hermes-telegram-check
```

If Notion publishing succeeded while Telegram was missing or unavailable, Intelligence Hub queues the notification in a local outbox. After Telegram credentials are configured, flush pending notifications:

```powershell
python scripts/telegram_flush_outbox.py
.\scripts\telegram_flush_outbox.ps1
```

The outbox sends only notifications that already have a real Notion URL. Failed sends remain pending with an incremented attempt count and last error.

Pipeline failure alerts are separate from normal brief notifications. When a production-facing `run_*.py` command crashes after opening memory, Intelligence Hub records a failed `runtime_runs` row and sends a Telegram alert when credentials are configured. Alerts are rate-limited per pipeline for one hour to avoid repeated notifications from the same failing scheduled task.

Preview Notion workspace database provisioning payloads:

```powershell
python scripts/provision_notion_workspace.py --print-payloads
.\scripts\provision_notion_workspace.ps1 -PrintPayloads
```

Create the Notion workspace databases after `NOTION_TOKEN` and `NOTION_PARENT_PAGE_ID` are added:

```powershell
.\scripts\provision_notion_workspace.ps1 -Apply
```

Provisioning creates databases for daily/weekly/monthly briefs, papers, GitHub repositories, ecosystem radar records, decisions, Radar snapshots, and durable Radar entities.

Create the databases and write the returned ids back to `.env`:

```powershell
.\scripts\provision_notion_workspace.ps1 -Apply -UpdateEnv
```

This command is safe to rerun. Databases that already have ids in `.env` are reported as `existing`; Intelligence Hub only creates the missing databases and writes their returned ids.

If you do not use `-UpdateEnv`, copy the created database ids into `.env` manually:

```powershell
NOTION_DAILY_BRIEFS_DATABASE_ID=
NOTION_PAPERS_DATABASE_ID=
NOTION_GITHUB_REPOS_DATABASE_ID=
NOTION_ECOSYSTEM_DATABASE_ID=
NOTION_DECISIONS_DATABASE_ID=
NOTION_RADAR_SNAPSHOTS_DATABASE_ID=
NOTION_RADAR_ENTITIES_DATABASE_ID=
```

When these structured database ids are configured, daily publishing writes the daily brief plus GitHub repository, paper, and ecosystem records. If a structured database id is missing, Intelligence Hub reports that specific structured publish path as skipped while still publishing the brief when possible.

Build the weekly report from accumulated memory:

```powershell
python scripts/run_weekly_intelligence.py --start 2026-07-01 --end 2026-07-07
.\scripts\run_weekly_intelligence.ps1 -Start 2026-07-01 -End 2026-07-07
```

Weekly reports automatically include decisions whose `revisit_date` falls inside the weekly window. This keeps prior Read/Prototype/Watch calls from becoming stale.

Publish weekly report to Notion and notify Telegram after the required `.env` values are added:

```powershell
.\scripts\run_weekly_intelligence.ps1 -Start 2026-07-01 -End 2026-07-07 -PublishNotion -SendTelegram
```

Review due decisions as a standalone workflow:

```powershell
python scripts/run_decision_review.py --as-of 2026-07-07 --since 2026-07-01
.\scripts\run_decision_review.ps1 -AsOf 2026-07-07 -Since 2026-07-01
```

Publish the standalone decision review to Notion and notify Telegram:

```powershell
.\scripts\run_decision_review.ps1 -AsOf 2026-07-07 -Since 2026-07-01 -PublishNotion -SendTelegram
```

Build the monthly report from accumulated memory:

```powershell
python scripts/run_monthly_intelligence.py --start 2026-07-01 --end 2026-07-31
.\scripts\run_monthly_intelligence.ps1 -Start 2026-07-01 -End 2026-07-31
```

Publish monthly report to Notion and notify Telegram:

```powershell
.\scripts\run_monthly_intelligence.ps1 -Start 2026-07-01 -End 2026-07-31 -PublishNotion -SendTelegram
```

Build the Executive Dashboard from accumulated memory:

```powershell
python scripts/run_executive_dashboard.py --as-of 2026-07-31 --window-start 2026-07-01
.\scripts\run_executive_dashboard.ps1 -AsOf 2026-07-31 -WindowStart 2026-07-01
```

Publish the Executive Dashboard to Notion and notify Telegram:

```powershell
.\scripts\run_executive_dashboard.ps1 -AsOf 2026-07-31 -WindowStart 2026-07-01 -PublishNotion -SendTelegram
```

The Executive Dashboard includes an operational health section with pipeline run counts, failed run counts, pending Telegram notifications, and memory table row counts. Use it with `scripts\hermes_status.py` when diagnosing scheduled task behavior.

Build a Radar Snapshot from accumulated memory:

```powershell
python scripts/run_radar_snapshot.py --as-of 2026-07-31 --since 2026-07-01
.\scripts\run_radar_snapshot.ps1 -AsOf 2026-07-31 -Since 2026-07-01
```

Publish the Radar Snapshot to Notion and notify Telegram:

```powershell
.\scripts\run_radar_snapshot.ps1 -AsOf 2026-07-31 -Since 2026-07-01 -PublishNotion -SendTelegram
```

When `NOTION_RADAR_SNAPSHOTS_DATABASE_ID` is configured, Radar Snapshot publishing writes a structured database record. When `NOTION_RADAR_ENTITIES_DATABASE_ID` is configured, the Radar run also writes durable entity records for technologies, companies, repositories, papers, and other tracked entities. When `NOTION_DECISIONS_DATABASE_ID` is configured, the Radar run also writes the current top decisions into the Decisions database.

Export Intelligence Hub runtime memory to JSONL and Markdown for backup, review, or versioning:

```powershell
python scripts/export_memory.py --as-of 2026-07-31
.\scripts\export_memory.ps1 -AsOf 2026-07-31
```

By default, exports are written to `exports/memory-<date>/` and include entities, observations, relationships, decisions, briefs, and a Markdown index.

The Phase 5 local baseline note is stored at `tests\.capability_post_cleanup_baseline\phase5-baseline.md`. It records test collection count, retained baseline artifacts, and the verification commands expected before promoting further changes.

Run tests:

```powershell
pytest
```

Run through the Windows-friendly runner:

```powershell
.\scripts\run_hermes.ps1 -SmokeTest
.\scripts\run_hermes.ps1
.\scripts\run_hermes.ps1 -Topic "AI agent workflow orchestration"
```

Logs are written to `logs/hermes-YYYYMMDD-HHMMSS.log`.

Create a daily Windows scheduled task:

```powershell
schtasks /Create /TN "Intelligence Hub Daily" /SC DAILY /ST 08:00 /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File %CD%\scripts\run_hermes_orchestration.ps1" /F
```

Or install Intelligence Hub scheduled tasks through the repository script:

```powershell
.\scripts\install_scheduled_tasks.ps1 -LiveGitHub -LivePapers -LiveDomainRss -PublishNotion -SendTelegram -IncludeWeekly -IncludeMonthly -IncludeDashboard -IncludeRadar
```

Preview scheduled task commands without changing Windows Task Scheduler:

```powershell
.\scripts\install_scheduled_tasks.ps1 -DryRun -LiveGitHub -LivePapersWithCode -LiveDomainRss -PublishNotion -SendTelegram -ModelSynthesis -IncludeWeekly -IncludeMonthly -IncludeDashboard -IncludeRadar -IncludeDecisionReview
```

Adjust scheduled task times when needed:

```powershell
.\scripts\install_scheduled_tasks.ps1 -DryRun -IncludeRadar -RadarTime 09:10 -IncludeDecisionReview -DecisionReviewTime 09:15
```

Validate the intended production schedule plan without touching Windows Task Scheduler:

```powershell
python scripts/schedule_plan_check.py --validate-production
.\scripts\schedule_plan_check.ps1 -ValidateProduction
```

Use `-LivePapersWithCode` instead of `-LivePapers` in scheduled tasks when the paper workflow should prefer repository-linked papers.

Install the full cloud-first operating schedule with pro-tier synthesis and decision review:

```powershell
.\scripts\install_scheduled_tasks.ps1 -LiveGitHub -LivePapersWithCode -LiveDomainRss -PublishNotion -SendTelegram -ModelSynthesis -IncludeWeekly -IncludeMonthly -IncludeDashboard -IncludeRadar -IncludeDecisionReview
```

Production installs automatically run the go-live gate before creating Windows scheduled tasks. Use `-LiveGoLiveCheck` to include read-only live API verification in that gate. Use `-SkipGoLiveCheck` only for an intentional override.

`-ModelSynthesis` is passed to daily orchestration, weekly, monthly, and dashboard tasks. Radar and Decision Review publish and notify, but do not call the synthesis model directly.

After installing scheduled tasks, audit the installed Windows Task Scheduler entries:

```powershell
python scripts/audit_scheduled_tasks.py
.\scripts\audit_scheduled_tasks.ps1
```

The audit compares installed task names, commands, schedule types, and start times against the production schedule plan. For offline review, export `schtasks /Query /FO CSV /V` and pass it through `--from-csv` / `-FromCsv`.

Remove installed Intelligence Hub scheduled tasks:

```powershell
.\scripts\install_scheduled_tasks.ps1 -Action Remove -IncludeWeekly -IncludeMonthly -IncludeDashboard -IncludeRadar -IncludeDecisionReview
```

Preview task removal without changing Windows Task Scheduler:

```powershell
.\scripts\install_scheduled_tasks.ps1 -Action Remove -DryRun -IncludeWeekly -IncludeMonthly -IncludeDashboard -IncludeRadar -IncludeDecisionReview
```

Create a weekly Windows scheduled task:

```powershell
schtasks /Create /TN "Intelligence Hub Weekly" /SC WEEKLY /D MON /ST 08:15 /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File %CD%\scripts\run_weekly_intelligence.ps1" /F
```

Linux cron example:

```cron
15 8 * * * cd /opt/intelligence-hub && HERMES_MEMORY_DB=data/hermes_memory.sqlite HERMES_SYNTHESIS_MODE=hybrid HERMES_PRO_CALL_LIMIT=8 /opt/intelligence-hub/hub_env/bin/python -m hermes run ai_intelligence --publish-obsidian >> logs/cron-daily.log 2>&1
```

For fixture dry-runs on any platform, set `HERMES_MEMORY_DB` to an isolated path and keep production memory separate from test memory.

Create a monthly Windows scheduled task:

```powershell
schtasks /Create /TN "Intelligence Hub Monthly" /SC MONTHLY /D 1 /ST 08:30 /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File %CD%\scripts\run_monthly_intelligence.ps1" /F
```

Create a daily Executive Dashboard scheduled task:

```powershell
schtasks /Create /TN "Intelligence Hub Dashboard" /SC DAILY /ST 08:45 /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File %CD%\scripts\run_executive_dashboard.ps1" /F
```

Run the scheduled task manually:

```powershell
schtasks /Run /TN "Intelligence Hub Daily"
```

Delete the scheduled task:

```powershell
schtasks /Delete /TN "Intelligence Hub Daily" /F
```

Archive and optimize database memory (remove observations and decisions older than specified retention days and vacuum):

```powershell
python scripts/archive_memory.py --retention-days 90
python scripts/archive_memory.py --retention-days 90 --dry-run
```
