# Code Structure

Suggested repository layout for the implementation (separate from this documentation repository, or as a monorepo alongside it):

```
/api            — API tier (routing, auth, rate limiting)
/orchestration  — Planner, Router
/execution      — Search, Crawler, Browser, Extractor, Parser, Normalizer
/intelligence   — Memory, Graph, Ranking, Trust Engine, Synthesis
/monitoring     — Monitor, Alerting
/connectors     — Connector implementations, Skills registry
/storage        — Store adapters (relational, snapshot, graph, cache, queue, vector)
/observability  — Logging, metrics, tracing, trace assembly
/config         — Environment/feature-flag loading
```

Each top-level folder should map cleanly to a subset of [../architecture/MODULES.md](../architecture/MODULES.md), so ownership and dependency boundaries in code mirror the spec.
