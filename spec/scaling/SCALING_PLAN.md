# Scaling Plan

## Scaling axes
- **API/orchestration tiers** — stateless, scale horizontally with request volume.
- **Execution workers** — scale independently per primitive; Browser scales separately and more conservatively than Search due to per-session resource cost (see [RESOURCE_LIMITS.md](RESOURCE_LIMITS.md)).
- **Memory/Graph stores** — scale with cumulative data volume, not just request rate; retention policy ([../../docs/operations/data-retention.md](../../docs/operations/data-retention.md)) bounds unconstrained growth.
- **Job scheduler/queue** — scales with monitor volume, dominated by `minutely`-frequency monitors.

## Scaling triggers
Auto-scale execution workers on queue depth ([../data/QUEUE_SPEC.md](../data/QUEUE_SPEC.md)) and request latency, not just raw CPU, since I/O-bound waiting on third-party sites doesn't show up as CPU load.

See [CAPACITY_PLANNING.md](CAPACITY_PLANNING.md) for projected headroom requirements.
