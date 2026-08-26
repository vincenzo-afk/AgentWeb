# Retrieval Modes

AgentWeb exposes different levels of retrieval depth so developers can trade off speed, cost, and comprehensiveness depending on the task.

| Mode | Purpose | Typical behavior |
|---|---|---|
| **Flash** | Instant search and lightweight grounding | Provider search only, with bounded top-result ranking and minimal browsing; no follow-up page fetches |
| **Focus** | Mid-depth answer generation | Provider search followed by bounded fetch-and-extract of up to three top results before ranking and synthesis |
| **Dive** | Deep multi-source research | Provider search followed by bounded fetch-and-extract of up to five top results before comparison, ranking, and synthesis |
| **Monitor** | Continuous observation and alerting | Separate `/observe` surface for scheduled checks, change detection, diffing, and update delivery over time |

These modes make the platform more legible to developers while preserving the long-term goal of fully automatic orchestration — if you don't specify a solve mode, the planner picks `flash`, `focus`, or `dive` based on the task. `monitor` is an observation surface rather than a `solve` retrieval mode and is created through `/observe`.

```js
await internet.solve({ task: "...", mode: "flash" });  // fast, cheap
await internet.solve({ task: "...", mode: "dive" });    // thorough, slower
await internet.observe({ task: "...", mode: "monitor" }); // recurring
```

See [api/reference/solve.md](../api/reference/solve.md) and [api/reference/monitor.md](../api/reference/monitor.md) for request schemas.
