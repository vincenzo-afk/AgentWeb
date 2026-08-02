# Queue Spec

## Purpose
Backs asynchronous [Jobs](../../docs/core/jobs.md): `monitor_check`, `webhook_delivery`, `graph_update`, `snapshot_gc`, and `dive`-mode long-running `solve_run` execution.

## Model
At-least-once delivery with idempotent job handlers (jobs must tolerate being run more than once without side effects — e.g., `webhook_delivery` checks whether a delivery attempt already succeeded before sending again).

## Priority
`monitor_check` jobs for `minutely` frequency monitors get higher scheduling priority than `daily` ones, to preserve timeliness guarantees in [../../docs/operations/sla-slo.md](../../docs/operations/sla-slo.md).

## Dead-letter handling
Jobs failing after max retries ([../resilience/RETRY_POLICY.md](../resilience/RETRY_POLICY.md)) move to a dead-letter queue for manual/automated review rather than being silently dropped.
