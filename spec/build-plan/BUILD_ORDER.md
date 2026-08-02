# Build Order

Derived from [../architecture/DEPENDENCY_GRAPH.md](../architecture/DEPENDENCY_GRAPH.md) — build modules with no unmet internal dependencies first.

1. **Foundational, no dependencies:** Search, Memory (storage layer), Trust Engine, Parser
2. **Depends only on tier 1:** Crawler (Search, Parser), Extractor (Parser, Normalizer), Ranking (Trust Engine)
3. **Depends on tier 1+2:** Connector, Browser (Connector), Skills
4. **Depends on tier 1-3:** Planner (Skills), Router (Planner, Connector)
5. **Depends on tier 1-4:** Monitor (Memory, Router, Alerting), Graph (Extractor, Normalizer, Memory)
6. **Top of stack:** Synthesis (Ranking, Graph, Memory), Alerting (Memory diff output)

API tier and Observability pipeline are built in parallel with tier 1 since they don't depend on orchestration internals — see [PHASES.md](PHASES.md) for how this maps to calendar phases.
