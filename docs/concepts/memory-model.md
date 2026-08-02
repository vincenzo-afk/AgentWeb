# Memory Model

The memory layer is one of the most strategically important components of AgentWeb because it changes the economics and quality of retrieval over time. Instead of repeatedly treating the web as stateless, AgentWeb snapshots pages, computes hashes, compares versions, reuses previous extractions, and selectively refreshes only what changed.

```
Internet page -> snapshot -> hash -> compare -> reuse -> refresh changed sections only
```

Benefits:

- **Lower repeated fetch cost** — unchanged content isn't re-fetched or re-processed.
- **Faster response time** on recurring tasks.
- **Better monitoring and diff detection** — see [Event-Driven Internet](event-driven-internet.md).
- **Historical replay** for audits or explainability.
- **Stronger foundation for future learning and strategy reuse.**

The memory layer underlies both `internet.solve()` (reusing known facts about a target) and `internet.observe()` (detecting what changed since the last check). See [core/memory.md](../core/memory.md) for the implementation model and [api/reference/memory.md](../api/reference/memory.md) for direct access to stored snapshots.
