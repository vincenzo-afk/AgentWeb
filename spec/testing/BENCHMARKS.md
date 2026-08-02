# Benchmarks

## What's benchmarked
- Latency per [retrieval mode](../../docs/concepts/retrieval-modes.md), p50/p95/p99
- Cost per mode (compute + any third-party provider costs)
- Memory reuse rate (% of requests served partially/fully from cache) over a rolling window
- Citation coverage rate (% of synthesized claims with valid citations)
- Trust score calibration (sampled human evaluation vs. `trust_score`)

## Benchmark cadence
Run against a fixed evaluation task set on every release candidate, tracked over time to catch regressions before they reach [PERFORMANCE_TARGETS.md](PERFORMANCE_TARGETS.md) violations in production.

See [../../docs/research/economic-model.md](../../docs/research/economic-model.md) for why memory reuse rate and cost-per-recurring-task are treated as strategic, not just operational, metrics.
