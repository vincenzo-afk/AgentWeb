# Trust and Verification

Deeper discussion of why explainability and trust scoring are treated as core requirements rather than optional features.

## Why it matters

Grounded internet workflows are frequently used for decisions, monitoring, research, or compliance-sensitive tasks, where users need to inspect the basis of a result rather than accept a black-box output. A platform that can't show *why* a source was selected or *what* changed between checks is difficult to trust for anything beyond casual lookups.

## Verification layers

1. **Source-level trust scoring** — see [concepts/trust-model.md](../concepts/trust-model.md).
2. **Claim-level citation** — mapping specific answer text to specific evidence, see [api/citations.md](../api/citations.md).
3. **Run-level execution graphs** — full replayable record of what the system did, see [concepts/execution-graphs.md](../concepts/execution-graphs.md).
4. **Change-level diffing** — for monitored targets, showing exactly what changed and when, see [core/memory.md](../core/memory.md).

## Open questions

- How to represent disagreement between sources in synthesized output without overwhelming the reader.
- How to calibrate trust scores across very different domains (e.g., ecommerce pricing vs. regulatory filings) without a one-size-fits-all model.
- How much verification detail to surface by default vs. behind an "inspect" action, to avoid overwhelming casual users while still serving compliance-sensitive ones.
