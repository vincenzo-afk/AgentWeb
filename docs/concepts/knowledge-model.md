# Knowledge Model

The knowledge graph layer allows AgentWeb to move beyond retrieval into relationship-aware intelligence. A graph can connect companies, founders, repositories, releases, funding events, products, pages, and signals, enabling queries that are difficult for plain search systems to answer naturally.

Example graph-backed queries:

- Show startups competing with a given company that recently raised funding.
- Show products launched by companies mentioned in a certain documentation ecosystem.
- Track how a set of entities changed across sources over time.

The graph becomes more valuable as monitoring, extraction, and memory continuously feed it — every run potentially adds or updates nodes and edges, so the graph compounds in value over time rather than being built once.

This is a post-MVP capability (see [roadmap.md](../roadmap.md) Phase 2). See [core/knowledge-graph.md](../core/knowledge-graph.md) for implementation details and [guides/graph-powered-research.md](../guides/graph-powered-research.md) for usage patterns once available.
