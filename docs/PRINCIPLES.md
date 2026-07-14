# Principles

These principles govern HIP product design, Hermes runtime behavior, and future agent work.

## Signal Over Noise

HIP should reduce information volume.

A successful output is not a longer report. A successful output makes the important few items obvious and explains why the rest can wait.

## Decision Over Summary

Every meaningful item should end in a decision-support recommendation.

Summary alone is not enough. HIP must explain significance, context, uncertainty, and action.

## Knowledge First

New information should be connected to existing knowledge.

Important signals should link to technologies, companies, papers, repositories, timelines, concepts, and prior observations whenever possible.

## Evolution Over Snapshot

HIP should track how things change over time.

The product should prefer patterns, inflection points, and trajectory over isolated daily events.

## Memory Over Repetition

Hermes should not restart from zero every day.

The platform should remember what it has seen before, when it first appeared, how it changed, and whether the user's prior decision was correct.

## Evidence Before Confidence

Hermes should state confidence only after considering evidence quality.

Confidence must not be a tone. It must reflect source quality, source diversity, reasoning strength, and uncertainty.

## Long-Term Over Hype

HIP should resist short-term attention spikes.

Trending items are not automatically important. Durable importance should be judged by engineering value, adoption, momentum, ecosystem impact, and longevity.

## Notion as v1 Workspace

For v1, Notion is the presentation and review workspace.

Notion should not become the runtime control plane. Runtime configuration, credentials, scheduling, logs, and model routing belong in Hermes.

## Local-First and Honest

Hermes should remain runnable locally and honest about which tools and sources were actually used.

If live web, arXiv, GitHub, RSS, or Notion publishing did not run, Hermes must not imply that they did.

## Five-Year Value

Before building a core feature, ask:

Will this still create value five years from now?

If the answer is no, do not put it in the core product.
