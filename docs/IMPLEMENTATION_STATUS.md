# Intelligence Hub Implementation Status

## Implemented and Tested

### Milestone 4 Open-Source Release Candidate

- Platform-neutral FastAPI app exposes health, readiness, briefs, insights, entities, events, decisions, proposals, runtime runs, and runtime status.
- Static local dashboard covers overview, insights, knowledge, proposal review, briefs, and operations without external CDN dependencies.
- The installable `intelligence-hub` CLI provides demo, seed, daily fixture, serve, status, proposal review, Obsidian export, and safe demo reset commands.
- Zero-secret demo seed writes repeatable data to `data/demo/`, including accepted insights, events, decisions, briefs, proposal review records, runtime metrics, and an Obsidian vault.
- README and release docs now describe Intelligence Hub as the platform and Hermes as an optional integration / compatibility layer.
- CI includes pytest, compileall, smoke checks, fixture demo, release demo seed, API health smoke, and first-run validation.

### Phase 3 Release Readiness

- Git repository initialized with publish-safe `.gitignore` coverage.
- `scripts/pre_publish_audit.py` scans publishable files for common secret patterns.
- Root MIT `LICENSE` and README acknowledgements are in place.
- Visitor-first README documents the zero-secret demo, samples, architecture, workflow, quick start, optional integrations, and release boundaries.
- Static sample outputs and Daily Brief preview asset are committed.
- `scripts/first_run_check.py` validates the demo path in a clean temporary project tree using `.env.example`.
- `.env.example` and `docs/CONFIGURATION.md` document demo, production, and live-check configuration layers.
- CI covers pytest, compileall, smoke, acceptance, fixture demo, and first-run checks on Windows and Linux.
- `hermes doctor --profile demo` reports demo readiness without requiring optional production integrations.
- Troubleshooting, GitHub issue templates, PR template, security policy, changelog, and release checklist are present.

### Phase 2 Platform Contracts

- `IntelligenceBrief` canonical output contract with structured signal validation.
- `DecisionEngine` for action ranking, Top N selection, and rationale structure fallback.
- `IntelligenceEngine` for building daily canonical briefs from repository, paper, and domain results.
- `SynthesisPolicy` with `off`, `hybrid`, and `full` modes plus configurable pro-tier cap.
- `MemoryEngine` facade with schema version, synthesis metadata, DB size, row counts, and indexes.
- `AgentRegistry` with default `ai_intelligence` registration and registry dispatch helper.
- `BriefRenderer`, `BriefPublisher`, and `BriefDeliveryCoordinator` abstractions.
- `python -m hermes` CLI with `doctor`, `status`, `agents`, `demo`, and `run`.
- `contracts/` shared types layer; connectors no longer import core modules.
- Scoped `knowledge/` loader with declared keys and character limit.
- Zero-secret fixture demo under `examples/`.
- Committed sample Markdown outputs under `examples/samples/`.
- First-run verification script that runs the zero-secret demo in a clean temporary project tree.
- GitHub Actions matrix covers Windows and Linux.
- Daily, weekly, monthly, dashboard, radar, and decision-review pipeline results expose `intelligence_brief` and persist synthesis metadata.
- Top decision rationale generation can use pro-tier AI through `IntelligenceEngine` when a generator is available; deterministic fallback remains the no-secret path.
- Weekly and decision-review Telegram delivery now pass through `BriefDeliveryCoordinator` while preserving legacy outbox compatibility.
- Orchestration dispatches the daily `ai_intelligence` stage through `AgentRegistry` and can include decision review.
- Golden baseline test guards fixture daily decision action drift.
- ADRs document action ownership, vector DB deferral, and Markdown/Obsidian as the primary demo surface.

### Phase 0 Platform Boundary Correction

- Intelligence Hub is now documented as the product and platform owner.
- Platform Runtime responsibilities are collection, processing, orchestration, canonical persistence, intelligence generation, decision support, delivery, scheduling, and observability.
- Hermes is documented as an optional research-agent integration and compatibility entrypoint, not the owner of runtime, automation, delivery, model routing, or canonical state.
- `ResearchAgent` is the minimal research-agent protocol with `investigate`, `reflect`, and `propose_insights`.
- Existing `RunnableAgent`, `AgentRegistry`, `python -m hermes`, and script entrypoints remain compatible.
- Boundary tests verify that platform modules do not import the optional Hermes integration.
- Phase 0 intentionally did not move business logic, change database schema, add Proposal Store, add PostgreSQL, add FastAPI, add Docker, or rename public entrypoints. Later milestones added the proposal layer, canonical repository seam, FastAPI, and Dashboard.

### Platform Migration Phase 1 Runtime Facade

- `PlatformRuntime` is available from `core.platform_runtime` as the platform-neutral facade and composition root.
- `PlatformRuntime` assembles settings, `MemoryStore`, `MemoryEngine`, `SynthesisPolicy`, the default `AgentRegistry`, optional publisher clients, model routing, memory status, and fixture daily dispatch.
- `HermesRuntime` remains available from `core.runtime` as a legacy compatibility name over `PlatformRuntime`.
- `python -m hermes`, `main.py`, and existing script entrypoints remain compatible; pipeline bodies and database schema are unchanged.
- Repository protocol migration, Proposal Store, Proposal Gate, PostgreSQL, FastAPI, Docker, and Obsidian Phase B were not part of Phase 1. Later milestones added the repository seam, proposal layer, FastAPI, Dashboard, and Obsidian Knowledge Workspace v1.
- Obsidian Phase A characterization tests remain as legacy behavior coverage; Obsidian Knowledge Workspace v1 now owns the repository-driven daily projection.

### Milestone 2 Canonical Repository and Obsidian Knowledge Workspace v1

- `Repository` protocol and `SQLiteRepository` wrapper expose platform-neutral canonical reads over the existing `MemoryStore`.
- `PlatformRuntime` exposes the repository seam while preserving `MemoryStore`, `MemoryEngine`, CLI, scripts, and fixture behavior.
- Obsidian v1 is split into `ObsidianReadModelBuilder`, `ObsidianRenderer`, and `ObsidianPublisher`.
- Daily Obsidian publishing reads canonical SQLite data through `SQLiteRepository` instead of relying on transient daily pipeline result objects.
- Obsidian notes use stable canonical IDs and stable ID-based filenames so title and punctuation changes do not overwrite unrelated notes.
- Semantic WikiLinks are generated for canonical relationships, event involvement, decision evidence, brief contents, and dashboard navigation.
- User-owned note sections are preserved across regeneration, writes are atomic, and stale generated notes are recorded in `90 System/Stale Notes.md` instead of being deleted.
- The legacy `ObsidianClient` public API remains available for compatibility and characterization tests.
- PostgreSQL, migration framework, Docker Compose, and broad pipeline migration were not included in Milestone 2. Later milestones added Proposal Store, Proposal Gate, FastAPI, and Dashboard.

### Milestone 3 Proposal Trust Layer and Canonical Insight Engine

- `Proposal` typed payloads cover entity, relationship, event, insight, and synthesis proposals.
- `SQLiteProposalStore` adds idempotent SQLite tables for proposals and proposal metrics while preserving existing memory data.
- `ProposalGate` composes schema, evidence, confidence, conflict, and provenance validators.
- `ProposalTrustService` is the required seam for turning accepted proposals into canonical Entity, Relationship, Event, or Insight records.
- Canonical `Event` and `Insight` tables are additive; `WorldState` remains deferred.
- Daily pipeline submits deterministic event, insight, and synthesis proposals, records proposal metrics, and continues deterministic fallback when model synthesis fails.
- Canonical Insight identity is stable across daily reruns and does not duplicate on repeated fixture runs.
- Obsidian projection now emits `02 Insights/`, links Daily Briefs to accepted Insights, preserves full-path WikiLinks without `.md` targets, and adds `90 System/Rejected Proposals.md` plus `90 System/Needs Review.md`.
- `scripts/proposals.py` lists, revalidates, accepts, and rejects proposals without bypassing required schema/evidence/provenance validation.
- Hermes remains optional and can act as a future proposal producer, but it does not own canonical persistence.

### Model Provider Foundation

- Cloud-first OpenAI-compatible model adapter
- `load_settings()` defaults new environments to `HERMES_MODEL_PROVIDER=cloud`
- Legacy DeepSeek environment variables are accepted as cloud-model fallback inputs during migration
- `GH_TOKEN`, `TELEGRAM_TOKEN`, `TG_BOT_TOKEN`, and `TG_CHAT_ID` are accepted as credential fallback aliases
- Fast/pro model tier policy owned by the Platform Runtime
- Production go-live check requires fast/pro cloud model values to be distinct for token-cost control
- Research brief workflow routed to the pro tier
- Optional daily, weekly, monthly, and dashboard executive synthesis through the pro tier with explicit `--model-synthesis`
- Ollama local fallback remains available through `HERMES_MODEL_PROVIDER=ollama`
- Doctor checks cloud model configuration and can live-check the fast tier with `--live`

### Memory Foundation

- SQLite-backed memory store
- Entity upsert and alias lookup
- Observation history
- Entity relationships
- Decision records with enforced action contract
- Runtime run ledger for pipeline execution, Notion delivery status, Telegram delivery status, and published URLs
- Pipeline failure alerts record failed runtime runs and can notify Telegram with per-pipeline rate limiting
- Telegram notification outbox for Notion-published notifications that could not be sent immediately
- Memory table stats for operational health and baseline reporting
- JSONL and Markdown memory export for backup and audit
- Credential setup CLI and PowerShell runner for final GitHub, Telegram, and fast/pro model go-live values
- SQLite remains the default local repository mode and is not legacy-only.
- `Repository` and `SQLiteRepository` provide the current canonical repository abstraction over the existing store.
- Additive proposal, event, insight, and proposal metrics tables are initialized idempotently by the trust layer and `MemoryEngine`.

### GitHub Radar Foundation

- GitHub repository snapshot parser
- GitHub client adapter
- Public GitHub live checks can run unauthenticated for development, while production go-live still requires `GITHUB_TOKEN`
- Authenticated GitHub token setup check CLI and PowerShell runner
- Repository entity ingestion
- Star delta observation
- Open issue observation
- Latest release observation
- Latest pull request observation
- Latest issue activity observation
- Contributor sample observation
- Repository-to-technology relationship creation from GitHub topics
- Momentum label and decision generation

### Paper Radar Foundation

- Paper snapshot parser
- arXiv Atom feed parser
- arXiv client adapter
- Papers with Code client adapter
- Papers with Code repository enrichment into paper snapshots
- Papers with Code redirect fallback to Hugging Face Papers live source
- Paper watchlist query support
- Paper entity ingestion
- Paper-to-technology relationship creation
- Paper-to-repository relationship creation
- Paper-to-company relationship creation
- Decision generation based on relationship strength

### Daily Intelligence Foundation

- Daily GitHub intelligence orchestration
- Daily paper intelligence orchestration
- Daily domain signal intelligence orchestration
- Daily structured Notion publishing for GitHub repo, paper, and ecosystem records when database ids are configured
- Fixture-backed daily dry-run CLI
- Windows-friendly daily PowerShell runner
- Ranked decision lines
- Telegram notification object creation

### Weekly Intelligence Foundation

- Weekly report object
- Repository and paper result aggregation
- Weekly report generation from accumulated memory
- Due decision review integration from persisted decision revisit dates
- Windows-friendly weekly PowerShell runner
- Trend direction generation
- Top action ranking

### Decision Review Foundation

- Standalone due decision review workflow
- Decision review pipeline that records a `decision_review` brief in memory
- Structured Notion brief payload for decision reviews
- Telegram notification payload for decision reviews
- Windows-friendly Decision Review PowerShell runner

### Monthly Intelligence Foundation

- Monthly report object
- Monthly report generation from daily and weekly memory
- Structured monthly Notion payload through the monthly pipeline
- Monthly Telegram notification payload
- Windows-friendly monthly PowerShell runner

### Executive Dashboard Foundation

- Executive Dashboard generated from latest daily, weekly, and monthly memory
- Top action deduplication across time horizons
- Operational health section with pipeline run counts, failed runs, pending notifications, and memory table counts
- Dashboard Notion page publishing path
- Dashboard Telegram notification payload
- Dashboard delivery status persisted to memory
- Windows-friendly dashboard PowerShell runner

### Radar Snapshot Foundation

- Radar Snapshot generated directly from accumulated memory entities, observations, relationships, and decisions
- Radar Notion page publishing path
- Structured Radar Snapshot database publishing path
- Structured durable Radar Entity database publishing path
- Radar Entity Notion publishing uses upsert semantics by exact Name to avoid duplicate long-term records
- Structured Decisions database publishing path from Radar Snapshot top decisions
- Decision Notion publishing uses upsert semantics by exact Signal ID to preserve decision evolution
- Radar Telegram notification payload
- Windows-friendly Radar Snapshot runner
- Radar stage included in ordered orchestration by default

### Automation Orchestration

- Ordered daily orchestration runner
- Local end-to-end acceptance check that exercises fixture sources, memory, daily, weekly, monthly, dashboard, Radar, Decision Review, Notion publishing boundary, and Telegram notification boundary
- Optional weekly, monthly, and dashboard stages in the same process
- Windows-friendly orchestration PowerShell runner
- Single-entry scheduled task command documented
- Windows scheduled task install/remove script
- Scheduled task install/remove script supports dry-run previews
- Scheduled task installer supports configurable daily, weekly, monthly, dashboard, Radar, and Decision Review times
- Scheduled task plan validator for full production coverage without touching Windows Task Scheduler
- Installed scheduled task audit CLI and PowerShell runner that compare Windows Task Scheduler state against the production plan
- Scheduled task installer runs the go-live gate before production installs
- Scheduled task installer supports pro-tier model synthesis flags for daily, weekly, monthly, and dashboard runs
- Scheduled task installer supports optional weekly Decision Review
- Readiness doctor for local configuration and external API checks
- Windows-friendly doctor PowerShell runner
- Production go-live readiness gate for required cloud, GitHub, Notion, and Telegram configuration
- Windows-friendly go-live PowerShell runner
- Local operational status report for latest run/brief links, memory counts, delivery status, go-live credential gaps, and next commands
- Windows-friendly operational status PowerShell runner
- Final readiness audit that combines local acceptance, production schedule validation, go-live configuration, runtime memory status, latest Notion surfaces, Telegram outbox state, and credential readiness
- Final readiness audit can optionally include installed Windows scheduled task verification
- Windows-friendly readiness audit PowerShell runner
- Scheduler, readiness, and observability responsibilities belong to Intelligence Hub Platform Runtime and do not require Hermes to be installed.

### Multi-Domain Intelligence Foundation

- Generic domain signal snapshot parser
- RSS feed connector for live domain signal collection without API keys
- Domain radar ingestion into the shared entity/observation/relationship/decision memory
- Domain impact momentum tracking
- Domain weighted impact scoring across velocity, cross-signal links, strategic relevance, and novelty
- Decision rationales expose the PRD sections: Why now, What changed, Connects to, What to do, and Confidence
- Initial fixture-backed watchlists for Finance, Cybersecurity, Apple, NVIDIA, and Startup intelligence
- Domain signals included in daily decision ranking and Executive Dashboard memory flow

### Publishers

- Shared delivery status model for dry-run, skipped, published/sent, and failed states
- Plain Notion page publishing
- Structured Notion daily brief database payload
- Structured weekly brief database payload through the weekly pipeline
- Structured Notion paper database payload
- Structured Notion GitHub repository database payload
- Structured Notion ecosystem database payload
- Structured daily Paper, GitHub Repo, and Ecosystem Notion publishing uses upsert semantics
- Notion workspace database schema payloads for briefs, papers, GitHub repos, ecosystem records, decisions, and Radar snapshots
- Notion workspace database schema payload for durable Radar entities
- Notion workspace provisioning CLI and PowerShell runner
- Notion workspace provisioning can write created database ids back to `.env`
- Notion workspace provisioning skips databases that already have ids configured to avoid duplicate workspace creation
- Telegram notification payload
- Telegram setup check CLI and PowerShell runner
- Telegram outbox flush CLI and PowerShell runner
- Telegram sends are blocked unless the primary Notion publish status is `published`
- Daily and weekly delivery status persisted to memory
- Decision Review delivery status persisted to memory
- Notion and Telegram delivery failures are captured as failed statuses instead of crashing the reporting pipeline

## Live-Verified

These integrations were verified against external APIs during setup:

- arXiv API requests
- Papers with Code or Hugging Face Papers fallback requests
- Public GitHub API requests for watched repositories
- Authenticated GitHub API request with configured token
- Domain RSS requests for Finance, Cybersecurity, Apple, NVIDIA, and Startup watchlists
- Cloud model fast-tier request
- Notion database provisioning API calls
- Notion parent/database retrieval checks for all configured Intelligence Hub databases
- Telegram bot identity check
- Notion daily brief page/database write from a full live daily run
- Notion paper, GitHub repo, and ecosystem record writes from a full live daily run
- Notion weekly and monthly brief writes from accumulated memory
- Notion Radar Snapshot, Radar Entity, and Decision writes
- Notion Executive Dashboard page write
- Live-source daily dry-run for GitHub, Papers with Code/Hugging Face, and domain RSS with isolated memory and Obsidian output

## Implemented but Not Live-Verified

These adapters have code paths but were not live-called during tests:

- Telegram-linked Notion delivery in a full scheduled run
- Telegram API sends

Live verification requires valid external credentials and network access.

Papers with Code currently redirects to Hugging Face Papers. The paper connector handles that redirect and was live-verified through `--live-papers-with-code`.

## Not Yet Implemented

- Executive Dashboard native UI
- PostgreSQL repository implementation
- `DecisionPolicy` abstraction for RuleBased, ModelAssisted, and Hybrid policies
- Semantic interest filtering from `HERMES_INTEREST_PROFILE` / `HERMES_RELEVANCE_THRESHOLD`
- Specialized live APIs for Finance Intelligence
- Specialized live APIs for Cybersecurity Intelligence
- Specialized live APIs for Apple Intelligence
- Specialized live APIs for NVIDIA Intelligence
- Specialized live APIs for Startup Intelligence
- Full Hermes proposal producer migration

## Recently Completed Enhancements

- **Canonical repository and Obsidian workspace v1**: Added `Repository` / `SQLiteRepository`, repository-driven Obsidian read model, renderer, publisher, stable note identity, semantic WikiLinks, user-note preservation, and stale-note manifest.
- **Proposal trust layer and canonical insights**: Added typed proposals, SQLite proposal store, proposal gate validators, canonical Event/Insight persistence, daily proposal metrics, proposal CLI, and Obsidian Insight/review surfaces.
- **Installed scheduled tasks**: Installed 6 tasks in Windows Task Scheduler and fully audited.
- **Intelligence effectiveness hardening**: Added paper/domain decision deduplication, Top Decisions source diversity, baseline repository limits, summary condensation, and concrete next-step wording.
- **Production memory protection**: Rebuilt polluted production memory from live sources and added CLI guards that reject local dry-runs targeting `data/hermes_memory.sqlite`.
- **Parallel and Fault-Tolerant Collection**: Pipeline fetch for GitHub, papers, and RSS are parallelized and isolated so a single source failure doesn't crash the entire run.
- **Automatic Retry with Backoff**: Integrated robust API request retries across all connectors.
- **GitHub Trending Client**: Added client to dynamically search and ingest trending repositories in daily pipeline.
- **Notion Block & Detail Formatting**: Upgraded brief publishing to rich block types (headings, list items, quotes, dividers) and added detailed page body templates to GitHub Repos, Papers, and Ecosystem records.
- **Memory Archival Script**: Created `scripts/archive_memory.py` to archive and optimize database rows.
- **Phase 5 Intelligence Quality**: Added cloud synthesis fallback, pipeline failure Telegram alerts, Decision Intelligence rationale contracts, operational health dashboard content, and a Phase 5 baseline note.

## Verification

Current local verification:

```powershell
.\hub_env\Scripts\python.exe -m pytest tests -q
.\hub_env\Scripts\python.exe -m compileall contracts core connectors hermes workflows scripts main.py
.\hub_env\Scripts\python.exe scripts\smoke_test.py
.\hub_env\Scripts\python.exe scripts\doctor.py
.\hub_env\Scripts\python.exe -m hermes demo --date 2026-07-10
.\hub_env\Scripts\python.exe scripts\readiness_audit.py --as-of 2026-07-09
.\hub_env\Scripts\python.exe scripts\run_decision_review.py --as-of 2026-07-07 --since 2026-07-01
.\hub_env\Scripts\python.exe scripts\run_daily_intelligence.py --date 2026-07-09 --notion-url local://notion/dry-run
```

The smoke test, default doctor, and default readiness audit do not call external APIs, publish to Notion, or send Telegram messages.
