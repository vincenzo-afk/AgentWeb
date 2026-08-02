# Product Spec

## What AgentWeb is

An API and orchestration layer that accepts a described intent and returns a grounded, cited outcome, choosing internally among search, crawl, browser, extract, memory, graph, and monitor capabilities. See [docs/architecture.md](../../docs/architecture.md) for the execution pipeline.

## Primary surfaces

- `internet.solve(task)` — one-shot grounded research
- `internet.observe(task)` — recurring monitoring with change alerts
- Low-level primitives (`search`, `crawl`, `browser`, `extract`) for advanced/manual control
- Agent-native primitives (`plan`, `execute`, `diff`, `report`) — see [module-specs](../module-specs/) for internals

## Core guarantees

- Every synthesized answer includes citations (see [docs/api/citations.md](../../docs/api/citations.md))
- Every run produces a replayable execution graph (see [ARCHITECTURE/EXECUTION_GRAPH.md](../architecture/EXECUTION_GRAPH.md))
- Recurring targets benefit from memory reuse rather than full re-fetch

## Full requirements

See [BUSINESS_REQUIREMENTS.md](BUSINESS_REQUIREMENTS.md) and [docs/product-requirements.md](../../docs/product-requirements.md).
