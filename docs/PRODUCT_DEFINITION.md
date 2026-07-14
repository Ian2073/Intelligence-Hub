# Product Definition

Intelligence Hub is a personal intelligence platform.

The Platform Runtime is the core execution layer. Hermes is an optional research-agent integration and compatibility entrypoint.

The Platform Runtime collects, analyzes, reasons, scores, remembers, and publishes. The product is the user's intelligence workspace: a small daily surface for understanding important changes and making better decisions.

Intelligence Hub must be automation-first. The user should not manually collect sources, manually paste summaries, or manually decide which raw items belong in a review workspace. The Platform Runtime performs the work; Markdown/Obsidian and optional production publishers display the result.

## What HIP Is

Intelligence Hub is:

- an intelligence platform
- a decision-support system
- a signal compression engine
- a personal memory layer for technology and market evolution
- a repeatable workflow for turning sources into judgment

## What HIP Is Not

Intelligence Hub is not:

- a generic AI chatbot
- a Notion clone
- a Telegram bot
- a news aggregator
- an LLM summary tool
- a dump of links
- a dashboard full of unread items

## Public Demo vs Production Deployment

The open-source public demo is Dashboard plus Markdown/Obsidian:

- no API keys
- fixture-backed sources
- generated Dashboard served by the platform-neutral FastAPI app
- generated Obsidian vault under `data/demo/obsidian_vault/`
- committed samples under `examples/samples/`

The author's production deployment can add:

- Notion as a structured review workspace
- Telegram as a notification channel
- cloud LLM synthesis
- Windows scheduled tasks

Both paths share the same `IntelligenceBrief` contract, SQLite memory model, decision actions, and publisher boundaries.

## Release Candidate Experience

A new user should be able to clone the repository, install dependencies, run `scripts/intelligence_hub.py seed-demo`, start `scripts/intelligence_hub.py serve --seed-demo`, and inspect:

- Dashboard overview
- Insights
- Entity knowledge pages
- Events
- Decisions
- Proposal review
- Briefs
- generated Obsidian Vault

This is local-first single-user software, not a production multi-user SaaS.

## Primary User Experience

The user should open the selected review surface and quickly see:

- today's most important signals
- why they matter
- what technologies and companies they connect to
- what action the platform recommends
- what the platform is uncertain about
- how the signal relates to prior memory

The user should not need to inspect raw source lists unless they choose to drill down.

## Core Output Unit

The core output unit is the Intelligence Brief.

For the first agent, the output unit is:

AI Intelligence Brief

Required sections:

- Executive Summary
- Top Signals
- Why It Matters
- Technology Map
- Ecosystem Impact
- Evolution Context
- Recommended Action
- Intelligence Score
- Confidence
- Memory Links

## Presentation Strategy

The public path uses Markdown/Obsidian as the zero-secret intelligence workspace.

Notion is an optional production publisher and review surface. It is not the control plane.

The Platform Runtime is responsible for:

- automated source collection
- automated analysis
- automated signal scoring
- automated brief generation
- automated publishing
- scheduling
- source configuration
- prompts
- model routing
- logs
- workflow execution

Hermes is responsible only for optional research-agent capabilities when configured:

- autonomous research
- reflection
- personalized memory
- skill accumulation
- tool-driven investigation

Review surfaces are responsible for:

- presentation
- persistence
- search
- review
- cross-domain browsing
- manual annotation

## Long-Term Product Boundary

Intelligence Hub may later include a native dashboard. That dashboard should only be built after the intelligence model, publisher boundaries, scoring framework, and daily brief workflow are proven.

The dashboard is a future product surface. It is not the v1 product dependency.

## Automation Boundary

The correct v1 flow is:

```text
Platform Runtime automated workflow
  -> collect or receive inputs
  -> analyze and compress signals
  -> generate Intelligence Brief
  -> publish to Markdown/Obsidian or optional production publishers
  -> optionally notify the user
```

The incorrect v1 flow is:

```text
user manually gathers links
  -> user asks for summary
  -> user copies result into a review workspace
```

Manual runs are acceptable during development, but the product direction is automated processing by Hermes.
