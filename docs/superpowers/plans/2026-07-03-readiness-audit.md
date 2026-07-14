# Readiness Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one Hermes readiness audit command that summarizes whether the system can go live and exactly which requirements still fail.

**Architecture:** Keep existing checks authoritative: `acceptance` proves the local fixture loop, `doctor` proves go-live config, `schedule_plan` proves automation coverage, and `operational_status` proves runtime memory and delivery status. The new module only composes those signals into a concise report.

**Tech Stack:** Python dataclasses, existing Hermes core modules, pytest, PowerShell runner.

## Global Constraints

- Use Traditional Chinese in user-facing responses.
- Do not print secrets from `.env`.
- Default readiness audit must avoid external API calls.
- Exit code is `0` only when all readiness requirements pass.

---

### Task 1: Core Readiness Model

**Files:**
- Create: `core/readiness_audit.py`
- Test: `tests/test_readiness_audit.py`

**Interfaces:**
- Consumes: `AcceptanceReport`, `DoctorReport`, `SchedulePlan`, `HermesOperationalStatus`
- Produces: `ReadinessAuditReport`, `build_readiness_audit(...)`, `render_readiness_audit(...)`

- [ ] **Step 1: Write tests for ready and not-ready reports**

Run: `.\hub_env\Scripts\python.exe -m pytest tests\test_readiness_audit.py -q`

- [ ] **Step 2: Implement dataclasses and requirement composition**

Create requirement rows for memory, latest briefs, local acceptance, production schedule, go-live gate, pending notification outbox, GitHub credentials, and Telegram credentials.

- [ ] **Step 3: Render a Markdown report**

Include status, as-of date, requirement table, latest Notion links, and next commands.

- [ ] **Step 4: Run targeted tests**

Run: `.\hub_env\Scripts\python.exe -m pytest tests\test_readiness_audit.py -q`

### Task 2: CLI and PowerShell Runner

**Files:**
- Create: `scripts/readiness_audit.py`
- Create: `scripts/readiness_audit.ps1`

**Interfaces:**
- Consumes: `load_settings`, `MemoryStore`, `run_acceptance_check`, `run_go_live_check`, `build_schedule_plan`, `validate_production_schedule`
- Produces: terminal report and process exit code

- [ ] **Step 1: Add Python CLI**

Flags: `--as-of`, `--include-future`, `--live`, `--skip-acceptance`.

- [ ] **Step 2: Add PowerShell wrapper**

Mirror the common runner pattern and write logs to `logs/hermes-readiness-audit-*.log`.

- [ ] **Step 3: Verify CLI help and current audit behavior**

Run: `.\hub_env\Scripts\python.exe scripts\readiness_audit.py --help`

Run: `.\hub_env\Scripts\python.exe scripts\readiness_audit.py --as-of 2026-07-03`

Expected: help exits `0`; current audit exits `1` until GitHub and Telegram credentials are added.

### Task 3: Docs and Full Verification

**Files:**
- Modify: `docs/RUNBOOK.md`
- Modify: `docs/IMPLEMENTATION_STATUS.md`

**Interfaces:**
- Consumes: new audit command behavior
- Produces: documented operating command and updated status

- [ ] **Step 1: Document readiness audit**

Add the command near acceptance/go-live sections.

- [ ] **Step 2: Update implementation status**

List readiness audit as implemented and note current live blockers remain credentials.

- [ ] **Step 3: Run verification**

Run:

```powershell
.\hub_env\Scripts\python.exe -m pytest tests -q
.\hub_env\Scripts\python.exe scripts\acceptance_check.py --date 2026-07-03
.\hub_env\Scripts\python.exe scripts\schedule_plan_check.py --validate-production
.\hub_env\Scripts\python.exe scripts\go_live_check.py
.\hub_env\Scripts\python.exe scripts\readiness_audit.py --as-of 2026-07-03
```

Expected: pytest, acceptance, and schedule validation pass. `go_live_check.py` and `readiness_audit.py` exit `1` until `GITHUB_TOKEN`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID` are configured.
