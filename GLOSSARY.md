# Glossary

**Intent** — A goal described by a developer or agent (e.g., "compare these three products") that AgentWeb translates into a plan.

**Planner** — The component that determines what kind of internet work a task requires (search, crawl, browse, extract, monitor, or a combination).

**Router** — The component that selects the concrete execution path (which tools/sources) once the planner has determined a strategy.

**Execution layer** — The set of tools (search, crawl, browser, extraction, monitoring) that gather raw evidence from the live web.

**Memory layer** — Stores prior snapshots, hashes, and extracted states so repeated tasks reuse prior work and only refresh what changed.

**Graph layer / Knowledge graph** — Connects entities, relationships, and events extracted across sources into a queryable structure for multi-hop, relationship-aware questions.

**Ranking / Trust layer** — Scores sources and evidence for reliability and relevance before synthesis.

**Synthesis layer** — Produces the final grounded output: a cited answer, comparison, report, timeline, or structured JSON.

**Execution graph** — An inspectable record of everything a given run did: plan, searches, browser sessions, extraction steps, memory lookups, graph updates, ranking decisions, and synthesis.

**Retrieval modes** — Flash, Focus, Dive, and Monitor: preset depth/cost/comprehensiveness tradeoffs. See [retrieval-modes.md](docs/concepts/retrieval-modes.md).

**Internet Skills** — Reusable strategy templates for recurring task classes (e.g., "compare products," "monitor a competitor").

**Event-driven internet model** — Treating internet changes (a price drop, a new release, a policy update) as triggers that flow into detection, graph update, workflow, and notification, rather than only answering one-off queries.

**Snapshot** — A stored capture of a page's content/state at a point in time, used for hashing, comparison, and reuse.

**Diff** — A computed difference between two snapshots of the same target, used to detect and describe change.

**Trust score** — A computed measure of a source's reliability used in ranking and synthesis.

**Grounded output** — A result backed by cited, retrievable evidence rather than model-generated claims alone.

See also [docs/terminology.md](docs/terminology.md) for API-level terms and [docs/concepts/index.md](docs/concepts/index.md) for deeper explanations.
