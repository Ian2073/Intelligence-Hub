# Roadmap

The roadmap prioritizes durable decision value over feature volume.

## Current Product Baseline

Intelligence Hub has moved past the original v1-only loop. The implemented baseline now includes:

- local-first Platform Runtime behavior with compatibility CLI entrypoints
- platform-neutral `PlatformRuntime` facade with `HermesRuntime` compatibility
- cloud-first model routing with fast/pro tiers and Ollama fallback
- six intelligence pipelines: daily, weekly, monthly, dashboard, Radar, and Decision Review
- SQLite memory for entities, observations, relationships, decisions, briefs, runs, and notification outbox
- platform-neutral `Repository` / `SQLiteRepository` canonical read seam
- proposal trust layer for model, agent, and extraction outputs
- GitHub, paper, and multi-domain RSS signal collection
- structured Notion publishing for briefs, papers, repositories, ecosystem records, decisions, Radar snapshots, and Radar entities
- repository-driven Obsidian Knowledge Workspace v1 for daily fixture/demo output
- canonical Insight notes and proposal review surfaces in Obsidian
- FastAPI API, static local dashboard, repeatable release demo seed, and platform-neutral local CLI
- Telegram notification payloads, delivery status, and outbox flushing
- Windows Task Scheduler install, plan validation, and installed-task audit
- local acceptance, doctor, go-live, readiness, and operational status checks
- Phase 3 release readiness assets: license, samples, first-run check, CI expansion, troubleshooting, templates, security policy, changelog, and release checklist

## Completed: Milestone 4 Open-Source Release Candidate

Goal: make the project cloneable, runnable without secrets, understandable from the README, and demonstrable through a browser dashboard plus Obsidian vault.

Completed scope:

- FastAPI app with health/readiness, knowledge, proposal, runtime, and review endpoints
- local static dashboard for overview, insights, knowledge, proposals, briefs, and operations
- idempotent zero-secret demo seed and Obsidian export
- installable platform-neutral `intelligence-hub` CLI
- GitHub CI smoke coverage for demo seed and API health
- public README and release docs aligned around Intelligence Hub as the platform

Remaining caveat:

- The release candidate is local-first and single-user. Authentication, multi-user hosting, PostgreSQL, and full Hermes proposal-producer migration remain future work.

## Completed: v1 Notion Intelligence Workspace

Goal: prove the first useful loop from topic or source input to intelligence output in Notion.

Status: completed and expanded.

Completed scope:

- product docs and initial runtime boundaries
- Agent-readable `hermes/soul/` context and workflow prompts
- AI research brief workflow
- Notion publishing boundary
- structured Notion workspace schema and provisioning
- local-first runtime with explicit delivery status

Remaining caveat:

- Notion remains an optional configured-mode publisher. The local Dashboard is now the release-candidate review surface.

## Completed: v2 Real Source Connectors and Signal Scoring

Goal: move from topic-based briefs to source-grounded intelligence.

Status: completed for the generic source foundation.

Completed scope:

- GitHub repository connector and live checks
- arXiv and Papers with Code / Hugging Face Papers paper ingestion
- domain RSS connector
- source normalization and fixture-backed dry-runs
- decision ranking and source diversity
- structured Notion records for papers, repositories, and ecosystem items
- Telegram notification boundary
- local scheduling support

Remaining caveat:

- Domain-specific APIs for Finance, Cybersecurity, Apple, NVIDIA, and Startup intelligence are not yet implemented.

## Completed: v3 Memory and Evolution

Goal: stop restarting every day.

Status: completed for durable local memory and time-based reports.

Completed scope:

- SQLite-backed memory store
- entity upsert and alias lookup
- first/last observation history through persisted observations
- entity relationships
- decision records with revisit dates and action contract
- weekly and monthly reports from accumulated memory
- Radar snapshots from memory
- decision review workflow
- memory export and archival utilities

Remaining caveat:

- Memory schema migration and long-term performance monitoring should be formalized before very large history growth.

## Completed: Phase 2 Platform Contracts

Goal: turn the Phase 1 pipeline set into a platform with explicit models, engines, agents, and publisher boundaries.

Completed scope:

- `IntelligenceBrief` is the canonical output contract for new delivery and engine paths.
- `DecisionEngine` centralizes action ranking, Top N selection, and rationale structure validation.
- `IntelligenceEngine` builds briefs from current repository, paper, and domain results with cross-signal output.
- `SynthesisPolicy` supports `off`, `hybrid`, and `full`, plus pro-tier call caps and deterministic downgrade.
- `MemoryEngine` adds schema versioning, synthesis metadata persistence, row counts, DB size, and indexes.
- `AgentRegistry` registers `ai_intelligence` and `python -m hermes agents` exposes the registry.
- `BriefRenderer`, `BriefPublisher`, and `BriefDeliveryCoordinator` provide the new delivery abstraction.
- `python -m hermes demo` gives a zero-secret Markdown/Obsidian demo path.
- All six pipeline result types expose an `intelligence_brief` and persist synthesis metadata.
- Top decision rationale generation is connected to `IntelligenceEngine`, `SynthesisPolicy`, and `ModelRouter` when a generator is available.
- Daily orchestration is registry-dispatched and decision review can run inside orchestration.
- Fixture decision actions have a golden baseline.

Post-release follow-up:

- Live-verify Telegram after primary publisher success in a full scheduled production run.
- Add future domain agents only after `ai_intelligence` proves the contract.

## Completed: Phase 0 Platform Boundary Correction

Goal: make the architecture explicit that Intelligence Hub is the platform and Hermes is an optional research-agent integration.

Current status:

- `ResearchAgent` protocol is introduced as the minimal research-agent interface with `investigate`, `reflect`, and `propose_insights`.
- Existing `RunnableAgent` compatibility remains unchanged.
- Architecture docs define Platform Runtime ownership for collection, processing, orchestration, canonical persistence, intelligence generation, decision support, delivery, scheduling, and observability.
- Boundary tests prevent platform modules from importing the optional Hermes integration.

Phase 0 did not move business logic, change database schema, add a proposal store, add PostgreSQL, add FastAPI, add Docker, or rename public entrypoints. Later milestones added the repository seam, proposal trust layer, FastAPI, and Dashboard while keeping those earlier compatibility guarantees.

## Completed: Platform Migration Phase 1 Runtime Facade

Goal: establish a platform-neutral runtime facade without changing existing public entrypoint behavior.

Completed scope:

- `PlatformRuntime` exists in `core.platform_runtime`.
- `HermesRuntime` remains as a compatibility name over `PlatformRuntime`.
- Fixture daily execution can run through `PlatformRuntime` directly.
- Existing CLI and script entrypoints remain available.
- No pipeline body, database schema, Obsidian exporter, folder structure, Proposal Store, PostgreSQL, FastAPI, or Docker migration is included.

Follow-up:

- Broad publisher migration for weekly, monthly, dashboard, Radar, and decision-review Obsidian surfaces remains after the repository seam.

## Completed: Milestone 2 Canonical Repository and Obsidian Knowledge Workspace v1

Goal: introduce a repository protocol without changing the default local storage behavior.

Completed scope:

- `Repository` protocol around currently needed canonical reads.
- `SQLiteRepository` wrapper over the existing SQLite `MemoryStore`.
- Repository contract and compatibility tests.
- `PlatformRuntime` exposes the repository seam while preserving existing store-based callers.
- Obsidian v1 projection split into read model builder, renderer, and publisher.
- Daily Obsidian output is generated from canonical repository data.
- Stable ID-based note paths, semantic full-path WikiLinks, dashboard notes, stale manifest, atomic writes, and user-note preservation.

Out of scope for this phase:

- PostgreSQL implementation
- Docker database profile
- migration tool
- Proposal Store / Proposal Gate
- broad pipeline migration beyond daily Obsidian publishing

PostgreSQL should be handled in a later API/Docker phase or a dedicated Phase 2B.

## Completed: Milestone 3 Proposal Trust Layer and Canonical Insight Engine

Goal: make non-deterministic or extracted knowledge auditable before it becomes canonical.

Completed scope:

- typed Proposal model for entity, relationship, event, insight, and synthesis payloads
- SQLite proposal store with accepted/rejected/needs-review states and rejection reasons
- composable Proposal Gate validators for schema, evidence, confidence, conflicts, and provenance
- accepted proposal persistence into canonical Entity, Relationship, Event, and Insight records
- deterministic Canonical Insight Engine v1 for cross-source convergence and meaningful status-change events
- daily proposal metrics for proposals created, accepted, rejected, needing review, canonical creates/updates, and insight count
- Obsidian Insight notes, rejected proposal surface, needs-review surface, and Daily Brief links to accepted Insights
- platform-neutral `scripts/proposals.py` for proposal review operations

Out of scope:

- PostgreSQL
- FastAPI or web dashboard
- complete optional Hermes proposal-producer migration
- WorldState as a parallel model
- multi-agent debate or automated high-risk conflict acceptance

## Completed: Phase 3 Release Readiness

Goal: make Intelligence Hub ready for a public GitHub repository without adding large new product scope.

Completed scope:

- Git repository initialized with ignored secrets, local databases, logs, and generated output.
- MIT license and acknowledgements are in place.
- Secret audit script passes against publishable files.
- Zero-secret demo samples, preview image, and first-run check are available.
- Public documentation is aligned around Dashboard plus Obsidian demo and optional configured-mode publishers.
- CI covers tests, compileall, smoke, acceptance, fixture demo, and first-run checks on Windows and Linux.
- Troubleshooting, GitHub issue templates, PR template, security policy, changelog, and release checklist are in place.

## Deferred: Semantic Interest Filtering

Natural-language interest profiling and relevance thresholds remain deferred. The config keys are reserved, but the pipeline is not wired to perform semantic interest filtering yet.

Post-release work should define tests, storage, scoring behavior, and user-facing semantics before enabling `HERMES_INTEREST_PROFILE` or `HERMES_RELEVANCE_THRESHOLD`.

## In Progress: v4 Multi-Domain Decision Intelligence

Goal: expand beyond AI while preserving the same decision-support contract.

Current status:

- Finance, Cybersecurity, Apple, NVIDIA, and Startup watchlists exist through domain RSS fixtures/live feeds.
- Domain signals are included in daily ranking and dashboard memory flow.
- Cross-signal insights connect repeated themes across GitHub, papers, and domain sources.

Next work:

- strengthen cross-signal analysis with memory relationships and semantic entity linking
- promote AI-generated decision rationale where it adds judgment quality
- define a pluggable domain-agent interface instead of letting workflows become the agent abstraction
- add specialized live APIs where RSS is too shallow

Success criteria:

- each domain has a clear boundary and source strategy
- each domain produces comparable decisions and confidence
- top decisions reflect cross-domain context, not only per-source scoring

## In Progress: Phase 5 Intelligence Quality

Goal: make Intelligence Hub more useful by improving judgment, not just collection.

Current status:

- `--model-synthesis` exists for daily, weekly, monthly, and dashboard pipelines.
- Production schedule validation requires model synthesis for daily, weekly, monthly, and dashboard tasks.
- Deterministic fallback remains available for CI, fixtures, and cloud-model failures.
- Decision rationales expose why now, what changed, connections, action, and confidence.

Next work by ROI:

1. Run a five-day observation period with production scheduled tasks using `-ModelSynthesis`.
2. Compare model-assisted briefs against deterministic fallback briefs for decision quality.
3. Expand high-value rationale generation through `DecisionEngine` with deterministic fallback.
4. Feed stronger cross-signal insights into Top Decisions ranking.
5. Add readiness audit evidence for Telegram-linked primary publisher delivery.

Success criteria:

- daily review takes minutes rather than source-by-source inspection
- top decisions explain why action is needed now
- model failure degrades gracefully to deterministic output
- notification status is fully auditable

## Completed: Local Intelligence Hub Dashboard

The local FastAPI Dashboard now provides the release-candidate review surface.

Implemented scope:

- Today Signals
- Intelligence Scores
- Watchlist changes
- technology evolution map
- recommended actions
- memory and entity drill-down
- operational status and delivery health

Current boundaries:

- local-first single-user operation
- Notion remains an optional configured workspace
- authentication and multi-user hosting are deferred

## Current High-ROI Backlog

1. Keep README, architecture, implementation status, and roadmap aligned after capability changes.
2. Maintain CI for pytest, compileall, smoke, demo, acceptance, and first-run validation.
3. Complete Telegram end-to-end live verification after Notion publish.
4. Migrate remaining Obsidian surfaces through the repository-driven projection seam.
5. Migrate Hermes research outputs into proposal producer adapters.
6. Improve decision rationale quality with model-assisted synthesis and fallback through a future `DecisionPolicy` abstraction.
