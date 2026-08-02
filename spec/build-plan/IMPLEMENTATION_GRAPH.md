# Implementation Graph

A task-level view of [BUILD_ORDER.md](BUILD_ORDER.md), showing which tasks can proceed in parallel vs. which block others.

```
[Search] ─┐
[Parser] ─┼─▶ [Crawler] ─┐
[Memory] ─┘              ├─▶ [Monitor] ─▶ [Alerting]
[Trust Engine] ─▶ [Ranking] ─┐            
[Normalizer] ─▶ [Extractor] ─┼─▶ [Synthesis]
[Connector] ─▶ [Browser] ─┐  │
[Skills] ─▶ [Planner] ─▶ [Router] ┘
[Extractor]+[Normalizer]+[Memory] ─▶ [Graph] ─▶ [Synthesis (graph-aware)]
```

Parallelizable tracks: (Search/Parser/Memory/Trust-Engine) can all start simultaneously with no cross-dependencies. See [MODULE_DEPENDENCIES.md](MODULE_DEPENDENCIES.md) for the full pairwise dependency list.
