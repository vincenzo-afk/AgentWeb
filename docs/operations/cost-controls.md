# Cost Controls

## Levers available to customers

- **Mode restrictions** — cap which [retrieval modes](../concepts/retrieval-modes.md) a given API key can use (e.g., disallow `dive` on a key used for a high-volume automated pipeline).
- **Monitor frequency limits** — set organization-wide caps on `minutely` monitors, which are the most expensive recurring cost driver.
- **Usage alerts** — configure thresholds via [`/admin/usage`](../api/reference/admin.md) to get notified before overspend.
- **Idempotency** — use [idempotency keys](../api/idempotency.md) to avoid accidental duplicate billed calls on retry.

## Diagnosing a cost spike

1. Check the mode distribution in `/admin/usage` — a shift toward `dive` or an increase in `monitor_checks` is the most common driver.
2. Check cache/memory reuse rate — a regression here means more full re-fetches than expected; see [operations/monitoring-stack.md](monitoring-stack.md).
3. Check for runaway or duplicated monitors (e.g., the same target being watched by multiple monitors unintentionally).

See [research/economic-model.md](../research/economic-model.md) for the underlying cost model.
