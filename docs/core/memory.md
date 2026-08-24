# Memory (Core Implementation)

Implements the conceptual model described in [concepts/memory-model.md](../concepts/memory-model.md):

```
Internet page -> snapshot -> hash -> compare -> reuse -> refresh changed sections only
```

## Components

- **Snapshot store** — captures page/content state at a point in time, keyed by target.
- **Hashing** — content-level hashing (and, where useful, field-level hashing) to detect meaningful change cheaply, without full re-diffing.
- **Diff engine** — computes structured differences between two snapshots, feeding [Monitoring](monitoring.md) alerts.
- **Reuse policy** — decides when cached extraction is "fresh enough" to skip re-fetching, based on task recency requirements and target volatility.

## Retention

Snapshot and crawl-history retention follow the policy in [operations/data-retention.md](../operations/data-retention.md). `agentweb gc` can purge expired records immediately, while `agentweb gc --schedule` stores one bounded `retention_gc` job for the supervised worker. The job can target one organization or all local organizations, uses the same lease/retry/dead-letter boundary as other scheduler jobs, and is coordinated through PostgreSQL when distributed queue mode is explicitly enabled; historical replay for audits depends on the retained window.

See [api/reference/memory.md](../api/reference/memory.md) for direct access.
