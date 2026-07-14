# Notion Workspace

Notion is the v1 presentation layer for HIP.

It is the intelligence workspace, not the runtime control plane.

## Responsibilities

Notion should handle:

- presentation
- persistence
- search
- review
- manual annotations
- cross-domain browsing
- long-term archive

Hermes should handle:

- source collection
- model routing
- prompt execution
- scheduling
- API keys
- logs
- workflow state
- publishing

## Workspace Structure

```text
Intelligence Hub
  Dashboard
  AI Research
    AI Research Daily Briefs
    Papers
    GitHub Repos
    AI Ecosystem
  Finance
    Finance Daily Briefs
    Market Watch
    Companies
    Macro Events
    Investment Notes
  Tech News
    Tech News Daily Briefs
    Tech Events
    Companies and Products
    Developer Tools
```

The main page should contain entry points and short linked views. It should not expand every database in full.

Current daily publishing writes the Daily Brief first. When the corresponding database ids are configured, Hermes also writes structured Paper, GitHub Repo, and AI Ecosystem records so radar databases accumulate independently from the daily brief text. These structured daily records use upsert semantics: Papers are matched by exact `URL`, while GitHub Repos and AI Ecosystem items are matched by exact `Name`. Radar publishing writes both a Radar Snapshot and durable Radar Entity records when their database ids are configured. Missing structured database ids are reported as skipped instead of failing the whole publish.

## Dashboard

The Dashboard should show:

- recent Daily Briefs
- today's key signals
- high-score items
- recommended actions
- domain entry points

If Notion cannot create a clean cross-database view, keep separate linked views for each domain.

## AI Research Page

The AI Research page should show:

- short description
- recent AI Research Daily Briefs
- links to Papers, GitHub Repos, and AI Ecosystem databases

## AI Research Daily Briefs

Suggested properties:

- Name: title
- Date: date
- Executive Summary: text
- Top Signals: text
- Recommended Actions: multi-select
- Intelligence Score: number
- Confidence: select
- Status: select
- Tags: multi-select
- Papers: relation to Papers
- GitHub Repos: relation to GitHub Repos
- Ecosystem Items: relation to AI Ecosystem

Suggested views:

- Table
- Calendar
- Published
- Drafts
- High Score

## Papers

Suggested properties:

- Title: title
- Authors: text
- URL: url
- Published Date: date
- Summary: text
- Why It Matters: text
- Technology Area: multi-select
- Intelligence Score: number
- Recommended Action: select
- Confidence: select
- Related Daily Brief: relation to AI Research Daily Briefs

## GitHub Repos

Suggested properties:

- Name: title
- URL: url
- Owner: text
- Stars: number
- Category: select
- Summary: text
- Why It Matters: text
- Engineering Value: select
- Adoption Potential: select
- Recommended Action: select
- Related Daily Brief: relation to AI Research Daily Briefs

## AI Ecosystem

Suggested properties:

- Name: title
- Type: select
- Company or Maintainer: text
- Category: multi-select
- Summary: text
- Why It Matters: text
- Impact: select
- Momentum: select
- Related Daily Brief: relation to AI Research Daily Briefs

## Decisions

Suggested properties:

- Name: title
- Action: select
- Rationale: text
- Expected Payoff: text
- Risk: text
- Revisit Date: date
- Confidence: select
- Signal ID: text
- Status: select

Hermes publishes Decisions with upsert semantics. It queries the Decisions database by exact `Signal ID`; if a page exists, Hermes updates its current action and review metadata, and if none exists, Hermes creates one. This lets a prior Watch, Read, or Prototype recommendation evolve without creating duplicate decision records.

## Radar Entities

Suggested properties:

- Name: title
- Type: select
- Status: select
- Last Seen: date
- Summary: text
- Tags: multi-select
- Observation Count: number
- Relationship Count: number

Radar Entities are the durable long-term layer for Technology Radar, Company Radar, Repository Radar, Paper Radar, and future domain radar views. Radar Snapshot explains what changed in a period; Radar Entities preserve the evolving state of each tracked object.

Hermes publishes Radar Entities with upsert semantics. It queries the Radar Entities database by exact `Name`; if a page exists, Hermes updates its properties, and if none exists, Hermes creates one. This prevents daily Radar runs from creating duplicate pages for the same technology, company, repository, or paper.

## Rules

- Field names should be stable and mostly English for API compatibility.
- Content can be written in Traditional Chinese.
- Notion should store outputs, not secrets.
- Notion should not contain API keys, prompt control, scheduler settings, or logs.
- Databases should be independent database pages.
- Domain pages should contain short descriptions, recent linked views, and database entry points.
