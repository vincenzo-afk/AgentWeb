# Runbooks

Operational playbooks for common incident types.

## Elevated error rate on `/solve`

1. Check [monitoring-stack.md](monitoring-stack.md) dashboards for error type breakdown (`upstream_error` vs. `internal_error`).
2. If `upstream_error` dominates, check whether a specific source/domain is down or blocking requests — isolate via the affected [execution graphs](../concepts/execution-graphs.md).
3. If `internal_error` dominates, check recent deploys and roll back if correlated.

## Monitor checks not firing

1. Confirm the monitor's `status` is `active` via [`GET /observe/{id}`](../api/reference/monitor.md).
2. Check the [Jobs](../core/jobs.md) queue for backlog on `monitor_check` jobs.
3. Verify webhook delivery isn't failing silently — check `webhook_delivery` job failure logs and confirm the receiving endpoint returns 2xx.

## Browser session failures spiking

1. Check [core/browser-engine.md](../core/browser-engine.md) sandbox health/capacity.
2. Check whether a specific target site changed its structure or added bot-detection, causing systematic failures.

## Cost spike

See [cost-controls.md](cost-controls.md) for diagnosis steps (mode distribution, monitor frequency, cache-hit-rate regression).
