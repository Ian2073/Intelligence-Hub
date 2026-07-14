# Intelligence Effectiveness Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve daily intelligence output quality by removing duplicate decisions, diversifying Top Decisions, lowering baseline-only noise, and making summaries/actions directly usable.

**Architecture:** Keep collection and ingestion APIs stable. Add ranking/deduplication in `workflows/daily_intelligence.py`, summary condensation in `core/daily_pipeline.py`, and action wording in radar result brief lines.

**Tech Stack:** Python dataclasses, pytest, existing `MemoryStore`, existing radar result objects.

## Global Constraints

- Use Traditional Chinese for user-facing text.
- Preserve existing external connectors and dry-run behavior.
- Do not send Telegram or publish Notion during verification.
- Keep changes scoped to daily intelligence ranking, summary, and presentation.

---

### Task 1: Decision Deduplication And Diversity

**Files:**
- Modify: `workflows/daily_intelligence.py`
- Test: `tests/test_daily_intelligence.py`

**Interfaces:**
- Consumes: `RepositoryRadarResult`, `PaperRadarResult`, `DomainRadarResult`
- Produces: `_select_top_results(...) -> tuple[...]` and `_decision_identity(result) -> str`

- [ ] Add tests proving duplicate paper/domain signal IDs appear once in notification decisions.
- [ ] Add tests proving Top Decisions include diverse sources when available.
- [ ] Implement `_select_top_results` with source/entity/topic dedupe and source diversity.
- [ ] Run `.\hub_env\Scripts\python.exe -m pytest tests\test_daily_intelligence.py -q`.

### Task 2: Baseline Noise Control

**Files:**
- Modify: `workflows/daily_intelligence.py`
- Test: `tests/test_daily_intelligence.py`

**Interfaces:**
- Consumes: repository `star_delta`, `momentum`, decision action, observations.
- Produces: ranking score that favors true change over first-day baseline.

- [ ] Add tests where baseline repos with `+0` stars do not crowd out cross-linked papers/domain signals.
- [ ] Implement score penalties for repository results with `star_delta == 0` and no strong release/change evidence.
- [ ] Keep major repository releases eligible for `Read`, but prevent them from dominating Top 7.
- [ ] Run `.\hub_env\Scripts\python.exe -m pytest tests\test_daily_intelligence.py -q`.

### Task 3: Summary Condensation

**Files:**
- Modify: `core/daily_pipeline.py`
- Test: `tests/test_daily_pipeline.py`

**Interfaces:**
- Consumes: `DailyIntelligenceRun.notification.decisions`, result objects, cross-signal insights.
- Produces: `_executive_summary(run) -> str` without duplicate highlights or truncated awkward text.

- [ ] Add tests proving executive summary does not repeat the same entity or action.
- [ ] Add tests proving summary first sentence prioritizes cross-source insight, then unique highlights.
- [ ] Implement unique highlight selection and sentence trimming by punctuation/word boundary.
- [ ] Run `.\hub_env\Scripts\python.exe -m pytest tests\test_daily_pipeline.py -q`.

### Task 4: Action Wording

**Files:**
- Modify: `core/paper_radar.py`
- Modify: `core/domain_radar.py`
- Modify: `core/github_radar.py`
- Test: existing radar tests and daily pipeline tests

**Interfaces:**
- Consumes: radar result context.
- Produces: brief lines that state what to do next, not only why the signal scored.

- [ ] Update paper brief lines to name the validation target.
- [ ] Update domain brief lines to name the reading/review target.
- [ ] Update GitHub brief lines to distinguish baseline tracking from prototype-worthy change.
- [ ] Run focused radar tests.

### Task 5: End-To-End Verification

**Files:**
- No code changes expected.

**Interfaces:**
- Produces: test evidence and isolated simulation output.

- [ ] Run `.\hub_env\Scripts\python.exe -m pytest`.
- [ ] Run `.\hub_env\Scripts\python.exe scripts\smoke_test.py`.
- [ ] Run isolated daily capability simulation and inspect Top Decisions.
- [ ] Confirm no duplicate entity dominates Top Decisions.
