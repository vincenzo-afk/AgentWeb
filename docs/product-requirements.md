# Product Requirements

This document summarizes the functional requirements behind the AgentWeb platform, organized by capability layer. It is the product-facing counterpart to [architecture.md](architecture.md) (which describes internal design) and [core/index.md](core/index.md) (which describes implementation).

## Functional requirements by layer

### Search
- Fast retrieval of web results, links, summaries, and candidate sources.
- Used when a task mainly requires discovery or fast answer generation.

### Crawl
- Structured traversal of websites, documentation collections, resource hubs, or content trees.
- Supports breadth over a domain, recurring indexing, and multi-page collection.

### Browser
- Rendering, interaction, navigation, and extraction from JavaScript-heavy or flow-dependent pages.
- Required for modern sites where static fetches are insufficient.

### Extract
- Transform raw pages into structured outputs: text, metadata, tables, lists, entities, prices, dates, links, summaries, normalized content.

### Monitor
- Ongoing observation of pages, entities, product listings, policy pages, docs, or releases.
- Produces alerts or triggers downstream workflows on change.

### Memory
- Store prior snapshots, hashes, extracted states, and historical versions.
- Avoid redundant work; support change comparison and historical replay.

### Graph
- Connect entities, organizations, products, events, releases, pages, and relationships into a queryable structure.
- Support multi-hop questions spanning sources, dates, and relationships.

### Synthesis
- Produce grounded outputs: cited answers, comparisons, reports, summaries, timelines, structured JSON.

## Non-functional requirements

- **Explainability** — every result must be able to expose its evidence path (sources, selection rationale, actions taken, changes detected).
- **Cost efficiency** — repeated tasks should leverage memory reuse rather than re-fetching and re-processing unchanged content.
- **Latency tiers** — retrieval modes (Flash/Focus/Dive/Monitor) must offer a legible speed/depth/cost tradeoff.
- **Auditability** — execution graphs must be replayable for debugging and compliance review.
- **Extensibility** — the platform must support custom connectors, rankers, and reusable "skills" without core changes.

## MVP requirements

See [roadmap.md](roadmap.md) Phase 0 for the minimal requirement set: one grounded-research endpoint, basic trust scoring, citation-backed output, page/price monitoring, and lightweight memory reuse.

## Out of scope (current phase)

- Full knowledge graph reasoning (Phase 2)
- Agent-native planning/execution APIs (Phase 3)
- Event-driven workflow automation (Phase 4)
