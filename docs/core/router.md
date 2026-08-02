# Router

The router takes the planner's output and selects concrete execution paths: which tools (search, crawl, browser, extract, monitor) and which sources to use.

## Responsibilities

- Map plan steps to concrete tool calls
- Select candidate sources for search/crawl steps
- Decide when a static fetch is sufficient vs. when a rendered [browser session](browser-engine.md) is required
- Balance cost/latency against the requested [retrieval mode](../concepts/retrieval-modes.md)
- Hand off gathered evidence to [Memory](memory.md) (for reuse checks) and ultimately [Synthesis](synthesis.md)

## Design notes

The router is deliberately separate from the planner so that routing strategy (which sources/tools to prefer) can evolve independently of task classification logic. This also makes it possible to swap or extend connectors (see [guides/building-connectors.md](../guides/building-connectors.md)) without touching planning logic.
