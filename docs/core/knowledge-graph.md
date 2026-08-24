# Knowledge Graph (Core Implementation)

Implements the conceptual model in [concepts/knowledge-model.md](../concepts/knowledge-model.md). The graph connects entities (companies, founders, repositories, releases, funding events, products, pages) and relationships extracted across runs and monitors.

## Population

The graph is populated incrementally:
- [Extraction](extraction.md) surfaces candidate entities and relationships from individual pages.
- [Monitoring](monitoring.md) and repeated runs update confidence and recency for existing edges.
- Cross-source corroboration increases edge confidence.

## Query model

Supports multi-hop, relationship-aware queries (e.g., "competitors of X that raised funding this month") that plain keyword search cannot answer directly. See [api/reference/graph.md](../api/reference/graph.md).

## Status

Implemented as an initial bounded local-first Phase 2 slice. The current runtime supports tenant-scoped SQLite entities and relations, provenance, corroboration-aware confidence, bounded one-to-three-hop traversal, case-insensitive name anchors, graph-assisted solve context, and cursor pagination. The implementation remains intentionally conservative about entity resolution and does not claim calibrated graph quality or general availability; those require an approved evaluation dataset and deployment plan. See [roadmap.md](../roadmap.md) Phase 2 and [../api/reference/graph.md](../api/reference/graph.md).
