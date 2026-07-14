# Scripts

The installable `intelligence-hub` command is the primary public interface. Scripts are retained for operational automation, release verification, and legacy compatibility.

## Primary Platform Commands

| Script | Status | Purpose |
| --- | --- | --- |
| `intelligence_hub.py` | Compatibility wrapper | Calls `core.cli:main`; prefer `intelligence-hub`. |
| `proposals.py` | Supported | Proposal list, revalidate, accept, and reject operations used by the platform CLI. |

## Release and Verification

| Script | Purpose |
| --- | --- |
| `smoke_test.py` | Fixture-backed model-routing and prompt-context smoke test. |
| `acceptance_check.py` / `acceptance_check.ps1` | Local end-to-end fixture acceptance. |
| `first_run_check.py` | Clean first-run demo verification. |
| `pre_publish_audit.py` | Git-index release hygiene scan. |
| `doctor.py` / `doctor.ps1` | Configuration and optional live readiness checks. |
| `go_live_check.py` / `go_live_check.ps1` | Strict configured-mode go-live gate. |
| `readiness_audit.py` / `readiness_audit.ps1` | Consolidated runtime and delivery readiness report. |

## Pipeline Operations

| Python script | PowerShell wrapper | Purpose |
| --- | --- | --- |
| `run_daily_intelligence.py` | `run_daily_intelligence.ps1` | Daily collection, decisions, proposal processing, and delivery. |
| `run_weekly_intelligence.py` | `run_weekly_intelligence.ps1` | Weekly brief generation. |
| `run_monthly_intelligence.py` | `run_monthly_intelligence.ps1` | Monthly brief generation. |
| `run_executive_dashboard.py` | `run_executive_dashboard.ps1` | Executive dashboard brief generation. |
| `run_radar_snapshot.py` | `run_radar_snapshot.ps1` | Radar snapshot generation. |
| `run_decision_review.py` | `run_decision_review.ps1` | Due-decision review. |

## Windows Scheduling

| Script | Purpose |
| --- | --- |
| `install_scheduled_tasks.ps1` | Creates, previews, or removes Windows scheduled tasks. |
| `schedule_plan_check.py` / `schedule_plan_check.ps1` | Validates the intended schedule without mutating Task Scheduler. |
| `audit_scheduled_tasks.py` / `audit_scheduled_tasks.ps1` | Compares installed tasks with the platform plan. |

The pipeline PowerShell wrappers are retained because the scheduled task installer invokes them and because they translate PowerShell switches into Python arguments.

## Integration Operations

| Python script | PowerShell wrapper | Purpose |
| --- | --- | --- |
| `configure_credentials.py` | `configure_credentials.ps1` | Updates `.env` without printing secrets. |
| `github_check.py` | `github_check.ps1` | GitHub connector configuration check. |
| `telegram_check.py` | `telegram_check.ps1` | Telegram configuration and optional send check. |
| `telegram_flush_outbox.py` | `telegram_flush_outbox.ps1` | Flushes queued notifications after delivery recovery. |
| `provision_notion_workspace.py` | `provision_notion_workspace.ps1` | Provisions configured Notion databases. |
| `export_memory.py` | `export_memory.ps1` | Exports runtime memory for review or backup. |
| `archive_memory.py` | — | Archives a selected memory database. |

## Legacy Hermes Compatibility

| Script | Purpose |
| --- | --- |
| `run_hermes.ps1` | Legacy research-brief launcher. |
| `run_hermes_orchestration.py` / `run_hermes_orchestration.ps1` | Legacy orchestration entrypoint over platform services. |
| `hermes_status.py` / `hermes_status.ps1` | Legacy status command. |

These entrypoints remain supported for compatibility. They do not make Hermes the owner of canonical persistence or platform execution.
