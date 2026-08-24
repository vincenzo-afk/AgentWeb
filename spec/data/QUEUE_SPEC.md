# Queue Spec

## Purpose
Backs asynchronous [Jobs](../../docs/core/jobs.md): `monitor_check`, `webhook_delivery`, `retention_gc`, `graph_update`, and `dive`-mode long-running `solve_run` execution. `retention_gc` carries bounded retention windows and an optional target organization; it purges local business records only through the owning worker’s memory/trace/metrics/audit boundaries.

## Model
At-least-once delivery with idempotent job handlers (jobs must tolerate being run more than once without side effects — e.g., `webhook_delivery` checks whether a delivery attempt already succeeded before sending again). `retention_gc` is safe to retry because expired-record deletion is monotonic and each organization/policy pair is coalesced into one pending job.

## Priority
`monitor_check` jobs for `minutely` frequency monitors get higher scheduling priority than `daily` ones, to preserve timeliness guarantees in [../../docs/operations/sla-slo.md](../../docs/operations/sla-slo.md).

## Dead-letter handling
Jobs failing after max retries ([../resilience/RETRY_POLICY.md](../resilience/RETRY_POLICY.md)) move to a dead-letter queue for manual/automated review rather than being silently dropped.
