# Automation

Hermes exists to automate intelligence work.

The local Dashboard and Obsidian Vault are the release-candidate review surfaces. Notion and Telegram are optional configured-mode publishers. Hermes is an optional integration and compatibility layer; platform runtime work belongs to Intelligence Hub.

## Product Intent

The user should not need to manually:

- collect links
- inspect every paper
- inspect every repository
- summarize items
- decide which items deserve a brief
- copy results into Notion
- remember what was seen before

Intelligence Hub should automate those steps and produce a small number of decision-ready outputs.

## v1 Automation Loop

The first practical loop is:

```text
Run Hermes
  -> load configuration
  -> load Hermes behavior context
  -> load workflow prompt
  -> generate AI Intelligence Brief
  -> publish to Notion if credentials exist
```

This is already a minimal automation loop, even if it is manually triggered during development.

## Target Automation Loop

The target loop is:

```text
Scheduled trigger
  -> collect sources
  -> normalize items
  -> deduplicate items
  -> score candidate signals
  -> select top signals
  -> reason over implications
  -> generate Intelligence Brief
  -> write structured records to Notion
  -> send notification if needed
  -> update memory
```

The current orchestration entrypoint can collect GitHub, arXiv or Papers with Code, and configured domain RSS sources before publishing and notification. Papers with Code is useful when the platform should prioritize papers that already have implementation evidence.

For production use, the scheduled loop should run cloud-first:

- fast tier for lower-cost extraction, classification, and cleanup
- pro tier only when `-ModelSynthesis` is enabled for final daily, weekly, monthly, or dashboard judgment
- deterministic local synthesis by default for fixture checks, scheduler validation, and no-token dry-runs

## Manual vs Automated

Manual execution is acceptable for development.

Manual collection is not the product.

The user can provide a topic or seed source, but Intelligence Hub should own the workflow after that point.

## Notion Publishing

Configured-mode Notion publishing should publish structured outputs:

- Daily Brief page
- related Paper records
- related GitHub Repo records
- related Ecosystem records
- Intelligence Score
- Confidence
- Recommended Action

The user should not be required to format these manually.

## Scheduler

The scheduler is the operating layer for Hermes Intelligence OS.

Recommended sequence:

1. Manual CLI run
2. Manual run with real source connectors
3. Scheduled local run
4. Notification after successful publish
5. Memory update after publish

The Windows scheduled task installer supports:

- daily ordered orchestration
- optional weekly report
- optional monthly report
- optional Executive Dashboard
- optional Radar Snapshot
- optional weekly Decision Review
- optional `-ModelSynthesis` for pro-tier executive synthesis

Daily, weekly, monthly, dashboard, Radar, and Decision Review task times can be adjusted through the scheduled task installer parameters (`-DailyTime`, `-WeeklyTime`, `-MonthlyTime`, `-DashboardTime`, `-RadarTime`, and `-DecisionReviewTime`).

The schedule plan can be validated without changing Windows Task Scheduler:

```powershell
python scripts/schedule_plan_check.py --validate-production
.\scripts\schedule_plan_check.ps1 -ValidateProduction
```

After scheduled tasks are installed, audit the actual Windows Task Scheduler state:

```powershell
python scripts/audit_scheduled_tasks.py
.\scripts\audit_scheduled_tasks.ps1
```

This audit compares installed task names, commands, schedule types, and start times against the production plan. Use it after installation so Hermes can prove that automation exists in Windows, not only in a documented command.

The final readiness audit can include this installed task check:

```powershell
python scripts/readiness_audit.py --check-scheduled-tasks
.\scripts\readiness_audit.ps1 -CheckScheduledTasks
```

Before installing production tasks, run the go-live gate. `doctor.py` is allowed to skip missing credentials for development; `go_live_check.py` treats missing production credentials, Notion database ids, Telegram settings, cloud model routing, and an incomplete production schedule plan as failures. The scheduled task installer also runs this gate automatically for production installs that use live sources, Notion publishing, Telegram notification, or model synthesis.

The weekly Decision Review task exists to prevent old Read, Prototype, Watch, or Ignore calls from becoming permanent assumptions.

## Automation Guardrails

Hermes must not report fake automation.

If a source connector did not run, the brief must not imply it used live sources.

If Notion publishing failed, Hermes must report failure clearly.

If Notion did not publish a real page, Telegram must not send a notification with a dry-run or placeholder link.

If confidence is low, Hermes must say why.
