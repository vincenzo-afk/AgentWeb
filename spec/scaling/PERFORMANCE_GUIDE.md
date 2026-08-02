# Performance Guide

## Levers for improving latency
- Increase memory reuse rate (biggest lever for recurring targets) — see [../module-specs/MEMORY_SPEC.md](../module-specs/MEMORY_SPEC.md).
- Prefer static fetch over Browser wherever the Router's escalation criteria allow — Browser sessions dominate p95 latency for the primitives that use them.
- Parallelize independent plan steps (e.g., searching multiple sources concurrently) rather than sequential execution — see [../architecture/REQUEST_FLOW.md](../architecture/REQUEST_FLOW.md).
- Cache short-lived, frequently-repeated calls (identical search queries) — see [../data/CACHE_SPEC.md](../data/CACHE_SPEC.md).

## Levers for reducing cost
See [../../docs/operations/cost-controls.md](../../docs/operations/cost-controls.md) (customer-facing) and [COST_MODEL.md](COST_MODEL.md) (internal cost structure).
