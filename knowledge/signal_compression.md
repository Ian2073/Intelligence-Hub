# Signal Compression

Signal Compression is the core behavior of HIP.

The platform may process:

- hundreds of papers
- hundreds of repositories
- news articles
- blog posts
- release notes
- social discussions

The user should receive only the few items that matter.

## Compression Goal

Compress many raw items into:

- top signals
- why they matter
- technology context
- ecosystem impact
- recommended action
- confidence
- memory links

## Bad Output

Bad output looks like:

```text
OpenAI announced...
Google released...
Meta published...
Here is a summary...
```

This is information collection, not intelligence.

## Good Output

Good output looks like:

```text
Signal: A new inference optimization technique is gaining adoption.
Why it matters: It changes the cost curve for local deployment.
Technology map: inference optimization, quantization, edge AI.
Ecosystem impact: affects model serving frameworks and local AI products.
Recommended action: Prototype.
Confidence: 72%, because adoption is visible but still early.
```

## Rule

If Hermes cannot explain why an item matters or what action it supports, the item should usually be ignored or watched rather than promoted.
