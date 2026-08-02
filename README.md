# AgentWeb

**An Internet Intelligence Platform for developers, businesses, researchers, and AI systems.**

AgentWeb gives you a single programmable layer for accessing, understanding, and monitoring the live internet — one API, one orchestration engine, one developer workflow. Instead of stitching together search APIs, crawlers, headless browsers, scrapers, page-change monitors, and citation pipelines yourself, you describe an intent and AgentWeb decides how to search, browse, extract, compare, reuse, monitor, rank, and return grounded results with transparent evidence.

> AgentWeb is an Internet Intelligence Platform that turns web intent into grounded outcomes using search, browser execution, memory, graph reasoning, monitoring, and transparent citations.

## Why AgentWeb

Modern applications that need live internet knowledge usually rely on fragmented tooling: a search API here, a scraper there, a browser automation framework somewhere else, plus hand-rolled ranking and citation logic. That fragmentation raises cost, latency, and maintenance burden, and it forces every team to solve the same orchestration problem independently.

AgentWeb replaces that stack with one outcome-first interface. You express a goal — research a company, compare products, track a competitor, watch for a visa slot — and the platform plans, executes, learns, and adapts automatically.

## Core capabilities

| Layer | Purpose |
|---|---|
| Search | Fast retrieval of links, summaries, and candidate sources |
| Crawl | Structured traversal across sites and documentation trees |
| Browser | Rendering, interaction, and extraction on JS-heavy or flow-dependent pages |
| Extract | Turning raw pages into structured, application-ready data |
| Monitor | Ongoing observation of pages, entities, and listings with change alerts |
| Memory | Snapshotting, hashing, and reusing prior page state to avoid redundant fetches |
| Graph | Linking entities, relationships, and events into queryable knowledge |
| Synthesis | Producing cited answers, comparisons, reports, and structured outputs |

## Quickstart

```js
const result = await internet.solve({
  task: "Find the cheapest RTX 6090 currently available in India and cite trustworthy sources"
});

const monitor = await internet.observe({
  task: "Track visa slot availability and alert when a new slot appears"
});
```

See [docs/getting-started](docs/getting-started/index.md) for a full walkthrough.

## Documentation map

- [Vision](docs/vision.md) — what AgentWeb is trying to become
- [Architecture](docs/architecture.md) — planner, router, execution, memory, graph, synthesis
- [Concepts](docs/concepts/index.md) — the ideas behind outcome-first internet access
- [API Reference](docs/api/index.md) — endpoints, requests, responses, errors
- [Core Systems](docs/core/index.md) — internals of each platform layer
- [Guides](docs/guides/index.md) — task-oriented how-tos
- [Research](docs/research/index.md) — whitepaper, landscape, economics
- [Operations](docs/operations/index.md) — running AgentWeb at scale
- [Security](docs/security/index.md) — threat model and compliance
- [SDKs](docs/sdk/index.md) — JavaScript, Python, REST

## Retrieval modes

AgentWeb exposes different depths of retrieval so you can trade off speed, cost, and comprehensiveness:

- **Flash** — instant search and lightweight grounding
- **Focus** — search plus selective browsing and extraction
- **Dive** — deep multi-source research with comparison and ranking
- **Monitor** — continuous observation, diffing, and alerting

See [retrieval-modes.md](docs/concepts/retrieval-modes.md) for details.

## Status

AgentWeb is under active design and development. The current MVP focuses on a single grounded-research endpoint with basic trust scoring, citations, and page-change monitoring. See the [roadmap](docs/roadmap.md) for what's next.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please also read our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

Licensed under the [MIT License](LICENSE).
