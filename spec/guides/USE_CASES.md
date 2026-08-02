# Use Cases

See [docs/vision.md](../../docs/vision.md) and [docs/research/user-segments.md](../../docs/research/user-segments.md) for the full narrative use-case catalogue by segment (AI/agent workflows, developer workflows, business/operations, research/analysis, consumer automation).

## Build-relevant use-case priority (for implementation sequencing)

| Use case | Modules primarily exercised | Phase |
|---|---|---|
| Grounded Q&A / research | Search, Extract, Ranking, Synthesis | 0 |
| Price/availability monitoring | Monitor, Memory, Alerting | 0 |
| Product comparison | Search, Browser, Extract, Synthesis | 1 |
| Documentation/release watching | Crawler, Monitor | 1 |
| Competitor relationship discovery | Graph | 2 |
| Autonomous multi-step research | Agent APIs, Skills | 3 |

This table exists to help prioritize which module combinations get the earliest end-to-end test coverage — see [../testing/SYSTEM_TESTS.md](../testing/SYSTEM_TESTS.md).
