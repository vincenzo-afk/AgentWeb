# Request Flow

## `solve` request, step by step

1. API tier authenticates the request and validates the schema ([../api/REQUEST_SCHEMA.md](../api/REQUEST_SCHEMA.md)).
2. Planner classifies the task and produces a plan ([../module-specs/PLANNER_SPEC.md](../module-specs/PLANNER_SPEC.md)).
3. Router maps plan steps to concrete tool calls ([../module-specs/ROUTER_SPEC.md](../module-specs/ROUTER_SPEC.md)).
4. Execution workers (search/crawl/browser/extract) run, in parallel where independent.
5. Memory checks for reusable prior state per target before each fetch ([../module-specs/MEMORY_SPEC.md](../module-specs/MEMORY_SPEC.md)).
6. Ranking scores gathered evidence ([../module-specs/RANKING_SPEC.md](../module-specs/RANKING_SPEC.md)).
7. Synthesis produces the cited answer ([../module-specs/SYNTHESIS_SPEC.md](../module-specs/SYNTHESIS_SPEC.md)).
8. API tier returns the response and persists the execution trace ([../observability/TRACING.md](../observability/TRACING.md)).

See [DATA_FLOW.md](DATA_FLOW.md) for what data moves at each step and [CONTROL_FLOW.md](CONTROL_FLOW.md) for branching/error paths.
