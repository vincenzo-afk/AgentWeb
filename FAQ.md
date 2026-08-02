# Frequently Asked Questions

**What is AgentWeb?**
An Internet Intelligence Platform that turns a described goal (an "intent") into a grounded, cited outcome, by automatically choosing and orchestrating search, browsing, extraction, memory reuse, and monitoring behind one API.

**How is this different from a search API?**
Search APIs return links or snippets. AgentWeb decides *how* to satisfy a task — which may involve searching, browsing dynamic pages, extracting structured data, comparing multiple sources, and/or setting up ongoing monitoring — and returns a synthesized, cited result along with the evidence path.

**How is this different from a browser automation tool?**
Browser automation is one layer inside AgentWeb (see [Browser](docs/core/browser-engine.md)), not the whole product. AgentWeb combines it with search, memory, extraction, ranking, and synthesis so you don't have to hand-write orchestration logic.

**Do I have to choose search vs. crawl vs. browser myself?**
No — that's the point. You describe the task via `internet.solve()` or `internet.observe()` and the planner/router choose the strategy. Advanced users can use lower-level primitives directly when they need explicit control.

**What are retrieval modes?**
Flash, Focus, Dive, and Monitor represent increasing depth (and cost) of retrieval. See [retrieval-modes.md](docs/concepts/retrieval-modes.md).

**How does monitoring work?**
The Memory layer snapshots and hashes pages so AgentWeb can detect what changed without re-fetching and re-processing everything. Monitors run on a schedule and trigger webhooks/alerts on detected changes. See [Monitor API](docs/api/reference/monitor.md).

**How do citations work?**
Every synthesized answer includes source attribution, and the platform can expose the execution path (which sources were selected and why) for inspection. See [citations.md](docs/api/citations.md) and [explainability.md](docs/concepts/explainability.md).

**Is there a knowledge graph?**
Yes, in the architecture — entities, relationships, and events extracted over time are linked into a queryable graph, enabling relationship-aware questions beyond keyword search. It is a post-MVP capability; see [roadmap.md](docs/roadmap.md).

**Can AI agents use AgentWeb directly?**
Yes. Agent-native APIs (`plan`, `execute`, `observe`, `diff`, `report`) are designed for autonomous systems that need inspectable, replayable internet access. See [agents.md](docs/concepts/agents.md).

**What's in the MVP vs. the long-term vision?**
See [roadmap.md](docs/roadmap.md) for a phase breakdown.
