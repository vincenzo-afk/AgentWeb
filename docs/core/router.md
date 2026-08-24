# Router

The router takes the planner's output and selects concrete execution paths: which tools (search, crawl, browser, extract, monitor) and which sources to use.

## Responsibilities

- Map plan steps to concrete tool calls
- Select candidate sources for search/crawl steps
- Decide when a static fetch is sufficient vs. when a rendered [browser session](browser-engine.md) is required
- Balance cost/latency against the requested [retrieval mode](../concepts/retrieval-modes.md)
- Hand off gathered evidence to [Memory](memory.md) (for reuse checks) and ultimately [Synthesis](synthesis.md)

## Current local implementation

The local MVP exposes a deterministic `Router.route(plan)` contract returning serializable `ToolCall` objects. It expands bounded URL lists into individual extraction or browser calls and maps the reusable aliases `search_each_item`, `extract_price_and_specs`, `rank_sources`, and `synthesize_comparison` to the corresponding local primitives. Browser calls preserve only the caller’s bounded action list and opaque `credential_id` or `session_state_id` references for the engine’s existing tenant/origin checks. Unsupported step types fail closed with a validation error.

## Design notes

The router is deliberately separate from the planner so that routing strategy (which sources/tools to prefer) can evolve independently of task classification logic. This also makes it possible to swap or extend connectors (see [guides/building-connectors.md](../guides/building-connectors.md)) without touching planning logic.
