# Performance Targets

| Mode | p95 latency target | Notes |
|---|---|---|
| `flash` | < 2s | Search-only, minimal browsing |
| `focus` | < 8s | Search + selective browsing/extraction |
| `dive` | < 60s | Recommend async/webhook beyond this |
| `monitor` check | Within configured frequency ± grace window | See [../module-specs/MONITOR_SPEC.md](../module-specs/MONITOR_SPEC.md) |

These match the SLOs in [../../docs/operations/sla-slo.md](../../docs/operations/sla-slo.md); this document is the build-time target set that operational SLOs are derived from and validated against in [BENCHMARKS.md](BENCHMARKS.md).
