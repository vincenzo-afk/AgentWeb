# Retrieval Modes

AgentWeb exposes different levels of retrieval depth so developers can trade off speed, cost, and comprehensiveness depending on the task.

| Mode | Purpose | Typical behavior |
|---|---|---|
| **Flash** | Instant search and lightweight grounding | Fast text-and-link retrieval from top results with minimal browsing |
| **Focus** | Mid-depth answer generation | Search plus selective browsing and extraction for stronger grounding |
| **Dive** | Deep multi-source research | Multi-step browsing, extraction, comparison, ranking, and synthesis across many sources |
| **Monitor** | Continuous observation and alerting | Scheduled checks, change detection, diffing, and update delivery over time |

These modes make the platform more legible to developers while preserving the long-term goal of fully automatic orchestration — if you don't specify a mode, the planner picks one based on the task.

```js
await internet.solve({ task: "...", mode: "flash" });  // fast, cheap
await internet.solve({ task: "...", mode: "dive" });    // thorough, slower
await internet.observe({ task: "...", mode: "monitor" }); // recurring
```

See [api/reference/solve.md](../api/reference/solve.md) and [api/reference/monitor.md](../api/reference/monitor.md) for request schemas.
