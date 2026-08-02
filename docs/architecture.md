# Architecture

AgentWeb's architecture is layered, with each stage contributing to a grounded and inspectable result. A simplified execution flow:

1. **Intent / task input** — the user or agent provides a goal.
2. **Planner** — determines what kind of internet work is needed. See [core/planner.md](core/planner.md).
3. **Router** — selects search, crawl, browser, extraction, or monitoring paths. See [core/router.md](core/router.md).
4. **Execution layer** — gathers raw evidence from the web through the chosen tools.
5. **Memory layer** — checks what has been seen before, what can be reused, and what changed. See [core/memory.md](core/memory.md).
6. **Graph layer** — links entities and relationships across retrieved evidence. See [core/knowledge-graph.md](core/knowledge-graph.md).
7. **Ranking / trust layer** — scores sources and evidence quality. See [core/ranking.md](core/ranking.md).
8. **Synthesis layer** — produces cited outputs or structured results. See [core/synthesis.md](core/synthesis.md).
9. **Report / response layer** — returns answer, sources, diffs, and execution transparency.

This stack supports both one-time research and ongoing intelligence workflows.

## Diagram (conceptual)

```
Intent ─▶ Planner ─▶ Router ─▶ Execution (search/crawl/browser/extract)
                                     │
                                     ▼
                              Memory (reuse/diff)
                                     │
                                     ▼
                              Graph (entities/relations)
                                     │
                                     ▼
                          Ranking & Trust scoring
                                     │
                                     ▼
                              Synthesis (cited output)
                                     │
                                     ▼
                       Report (answer + sources + diffs)
```

## Memory layer design

The memory layer changes the economics and quality of retrieval over time. Instead of treating the web as stateless, AgentWeb snapshots pages, computes hashes, compares versions, reuses previous extractions, and selectively refreshes only what changed:

```
Internet page -> snapshot -> hash -> compare -> reuse -> refresh changed sections only
```

Benefits: lower repeated fetch cost, faster response time on recurring tasks, better monitoring and diff detection, historical replay for audits, and a stronger foundation for future learning and strategy reuse.

## Knowledge graph design

The graph layer allows AgentWeb to move beyond retrieval into relationship-aware intelligence, connecting companies, founders, repositories, releases, funding events, products, pages, and signals. This enables queries that are difficult for plain search to answer, such as: "show startups competing with a given company that recently raised funding," or "track how a set of entities changed across sources over time." The graph becomes more valuable as monitoring, extraction, and memory continuously feed it.

## Explainability and trust

AgentWeb doesn't only return an answer — it shows the evidence path: which sources were used, why those sources were selected, what browser actions occurred, what changed between snapshots, and why a trust score is high or low. This matters because grounded internet workflows are often used for decisions, monitoring, research, or compliance-sensitive tasks where users need to inspect the basis of a result.

## Execution graph

Each request produces an inspectable graph of the plan and actions taken — planning, searches, browser sessions, extraction steps, memory lookups, graph updates, ranking decisions, and synthesis. This supports debugging, replay/audit, enterprise observability, and strategy optimization over time. See [concepts/execution-graphs.md](concepts/execution-graphs.md).

## Event-driven internet model

A long-term architectural direction treats the internet as an event stream rather than only a searchable document collection: a page changes, a price drops, a visa slot appears, a repository releases a version, or a policy page updates — AgentWeb detects the event, updates memory and graph state, triggers a workflow, and delivers the outcome. This shifts the platform from **Ask → Answer** to:

```
Internet changes -> detection -> graph update -> workflow trigger -> research -> notification -> downstream action
```

See [concepts/event-driven-internet.md](concepts/event-driven-internet.md).
