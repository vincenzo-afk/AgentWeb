# Tracing

## Purpose
Backs the [execution graph](../architecture/EXECUTION_GRAPH.md) concept — every planner decision, router selection, tool call, memory lookup, ranking decision, and synthesis step is captured as a span within a run's trace.

## Trace schema
```
ExecutionTrace {
  execution_id
  plan: Plan
  spans: [{ component, operation, start_time, end_time, input_summary, output_summary, status }]
  sources_considered: Source[]
  sources_used: Source[]
  trust_scores: { source_id: score }
}
```

## Retrieval
`GET /report/{execution_id}` returns the assembled trace — see [../../docs/api/reference/agents.md](../../docs/api/reference/agents.md) and [../../docs/getting-started/debugging-basics.md](../../docs/getting-started/debugging-basics.md).

## Constraint
Span `input_summary`/`output_summary` must never include full secret values or full raw page content bodies — summarize/hash instead, per [LOGGING.md](LOGGING.md)'s "never log" rule.
