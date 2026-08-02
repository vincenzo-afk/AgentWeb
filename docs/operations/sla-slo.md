# SLA / SLO

## Target SLOs (indicative)

| Metric | Target |
|---|---|
| API availability | 99.9% monthly |
| `flash` mode p95 latency | < 2s |
| `focus` mode p95 latency | < 8s |
| `dive` mode p95 latency | < 60s (async recommended beyond this) |
| Monitor check timeliness | within configured frequency ± grace window |
| Webhook delivery success rate | 99.5% (with retry) |

## Error budget

Availability and latency targets are tracked against an error budget per rolling 30-day window; sustained breaches trigger a reliability-focused work prioritization per [runbooks.md](runbooks.md).

## Exclusions

Degradation caused entirely by third-party target sites being unreachable (`upstream_error`) is tracked separately from platform-caused (`internal_error`) failures and is excluded from core availability SLOs, though it is still monitored.
