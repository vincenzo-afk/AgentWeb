# Dependency Graph

## Build-time / runtime module dependencies

```
Planner        depends on: Skills
Router         depends on: Planner, Connector
Search         depends on: (none internal)
Crawler        depends on: Search, Parser
Browser        depends on: Connector
Extractor      depends on: Parser, Normalizer
Monitor        depends on: Memory, Router, Alerting
Memory         depends on: (storage layer only)
Graph          depends on: Extractor, Normalizer, Memory
Ranking        depends on: Trust Engine
Trust Engine   depends on: (none internal)
Synthesis      depends on: Ranking, Graph (optional), Memory
Alerting       depends on: Memory (diff output)
```

This ordering directly informs [../build-plan/BUILD_ORDER.md](../build-plan/BUILD_ORDER.md) and [../build-plan/MODULE_DEPENDENCIES.md](../build-plan/MODULE_DEPENDENCIES.md) — modules with no unmet dependencies can be built and tested in parallel.
