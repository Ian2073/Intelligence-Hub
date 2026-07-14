# Automation

Intelligence Hub automates collection, normalization, proposal validation, insight generation, decision support, publishing, and run accounting.

## Platform Loop

```text
Scheduled or manual trigger
  → collect sources
  → preserve evidence
  → normalize deterministic records
  → create proposals for non-deterministic knowledge
  → validate proposals
  → persist accepted canonical knowledge
  → generate decisions and briefs
  → project to Dashboard, API, and Obsidian
  → optionally deliver to Notion or Telegram
```

## Manual and Scheduled Operation

Manual execution is appropriate for development and local review. Windows Task Scheduler support remains available for configured deployments.

```powershell
python scripts/schedule_plan_check.py --validate-production
.\scripts\install_scheduled_tasks.ps1 -DryRun -IncludeWeekly -IncludeMonthly -IncludeDashboard -IncludeRadar -IncludeDecisionReview
python scripts/audit_scheduled_tasks.py --minimal
```

The retained PowerShell wrappers translate Windows-friendly switches and are used by scheduled task installation. Their supported status is documented in `scripts/README.md`.

## Guardrails

- Do not report a live collector, model call, publish, or notification unless it ran.
- Model failure must degrade to deterministic output where supported.
- A failed Notion publish must not produce a Telegram notification with a placeholder link.
- Optional agents, including Hermes, submit proposals and do not write canonical knowledge directly.
- Default CI and fixture demos must not require credentials or external services.
