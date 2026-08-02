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

All metrics tagged with `org_id` where relevant, to support per-organization cost/usage reporting ([../api/RESPONSE_SCHEMA.md](../api/RESPONSE_SCHEMA.md) usage endpoints).
