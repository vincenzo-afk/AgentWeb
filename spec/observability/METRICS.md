# Metrics

## Core metrics emitted per component

| Metric | Type | Purpose |
|---|---|---|
| `request_count` | Counter, by endpoint/mode | Volume tracking |
| `request_latency` | Histogram, by endpoint/mode | Feeds [../testing/PERFORMANCE_TARGETS.md](../testing/PERFORMANCE_TARGETS.md) validation |
| `error_count` | Counter, by `error.type` | Feeds [../../docs/operations/monitoring-stack.md](../../docs/operations/monitoring-stack.md) dashboards |
| `memory_reuse_rate` | Gauge | Strategic efficiency metric, see [../../docs/research/economic-model.md](../../docs/research/economic-model.md) |
| `job_queue_depth` | Gauge, by job type | Backlog health, see [../data/QUEUE_SPEC.md](../data/QUEUE_SPEC.md) |
| `browser_session_success_rate` | Gauge | Highest-variance component health |
| `cost_per_run` | Histogram, by mode | Internal margin tracking |

All metrics tagged with `org_id` where relevant, to support per-organization cost/usage reporting ([../api/RESPONSE_SCHEMA.md](../api/RESPONSE_SCHEMA.md) usage endpoints). Request, error, observation, and gauge points are persisted in the local SQLite runtime store through `MetricStore`, so a process restart does not erase the diagnostic baseline. `/admin/metrics` filters to the requesting organization and never exposes another organization’s labeled values or global process aggregates; global points are available only from an explicitly unscoped internal snapshot. `agentweb gc --metric-days N` removes expired metric points; the cleanup operation supports an optional organization filter and reports its deletion count. Distributed PostgreSQL queue gauges continue to come from the shared coordinator when enabled.
