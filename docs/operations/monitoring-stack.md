# Monitoring Stack

Internal observability for the platform itself (distinct from AgentWeb's user-facing [Monitoring](../core/monitoring.md) capability).

## Key dashboards

- **Request volume and latency** by endpoint and [retrieval mode](../concepts/retrieval-modes.md)
- **Error rate** by `error.type` (see [api/errors.md](../api/errors.md))
- **Cache/memory reuse rate** — a core efficiency metric tied to the [Memory layer](../core/memory.md)
- **Job queue health** — backlog and failure rate per [job type](../core/jobs.md)
- **Browser session success rate** — surfaced separately since it's typically the highest-variance component
- **Cost per run** by mode, for internal margin tracking (complements customer-facing [cost-controls.md](cost-controls.md))

## Alerting

Alerts are tied to the [SLO targets](sla-slo.md); paging alerts are reserved for availability and error-rate breaches, while cost/efficiency regressions route to a lower-urgency channel for review.
