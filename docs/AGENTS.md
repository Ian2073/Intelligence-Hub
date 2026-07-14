# Agents

Agents are domain-specific intelligence workers.

They are not the core of HIP. The engines are the core. Agents use the engines to produce repeatable intelligence outputs for a domain.

## Agent Contract

Every Intelligence Agent is registered through `AgentRegistry` and must describe:

- `agent_id`
- `domain`
- supported ingestor types
- intelligence workflow
- synthesis policy
- supported publishers

Every Intelligence Agent should produce an `IntelligenceBrief` with:

- Executive Summary
- Top Signals
- Why It Matters
- Technology or Domain Map
- Ecosystem Impact
- Evolution Context
- Recommended Action
- Intelligence Score
- Confidence
- Memory Links

Every signal must answer:

- What happened?
- Why does it matter?
- What does it connect to?
- What changed compared with prior memory?
- What should the user do?
- How confident is the platform in this signal?

## First Agent: AI Intelligence

AI Intelligence tracks the core movement of AI technology.

It should cover:

- papers
- open-source repositories
- model releases
- framework releases
- infrastructure changes
- company research moves
- product shifts that affect AI builders
- technical debates with long-term implications

It should not produce a generic AI news digest.

Runtime status: `ai_intelligence` is registered by default through `core.agent_runtime.build_default_registry()` and can be listed with:

```powershell
.\hub_env\Scripts\python.exe -m hermes agents
```

It covers the current daily intelligence path: GitHub fixtures/live sources, papers, domain RSS, brief generation, and optional Obsidian/Notion/Telegram delivery.

## AI Intelligence Brief

Required sections:

### Executive Summary

Thirty-second overview of the most important changes.

### Top Signals

The small set of signals that deserve attention.

Each signal should include:

- title
- source type
- importance
- why it matters
- recommended action
- confidence

### Why It Matters

Explain the underlying technical or ecosystem significance.

### Technology Map

Place the signal into a technology route such as:

- model architecture
- inference optimization
- agent runtime
- RAG
- multimodal AI
- training infrastructure
- evaluation
- deployment
- AI developer tools

### Ecosystem Impact

Identify affected companies, repositories, frameworks, models, and users.

### Evolution Context

Explain how the item fits into a longer trend.

### Recommended Action

Use one of:

- Ignore
- Watch
- Read
- Prototype
- Implement
- Review later

### Intelligence Score

Score the importance of the signal, not the quality of the source.

Suggested dimensions:

- Importance
- Impact
- Momentum
- Engineering Value
- Adoption
- Longevity
- Novelty

The final score is weighted, not a simple average.

### Confidence

Confidence reflects the quality of the evidence and reasoning.

It should be low when sources are weak, early, single-source, promotional, or not verified.

## Future Agents

Future agents may include:

- Finance Intelligence
- Tech Intelligence
- Startup Intelligence
- Career Intelligence
- Apple Intelligence
- Security Intelligence
- Semiconductor Intelligence
- Robotics Intelligence
- Healthcare Intelligence
- Climate Tech Intelligence

Each new agent must reuse the same decision-support principles instead of becoming a separate news digest.
