# Debugging Basics

Every run produces an **execution graph**: a record of the plan and every action taken to produce a result. Use it to understand why a result looks the way it does, or why a monitor didn't fire.

```js
const trace = await internet.report(result.execution_id);

console.log(trace.plan);            // what the planner decided
console.log(trace.actions);         // search calls, browser sessions, extraction steps
console.log(trace.sources_considered);
console.log(trace.sources_used);
console.log(trace.trust_scores);
```

## Common things to check

- **Wrong mode used** — pass `mode` explicitly if you need to force Flash/Focus/Dive/Monitor rather than letting the planner choose. See [concepts/retrieval-modes.md](../concepts/retrieval-modes.md).
- **Missing sources** — check `sources_considered` vs. `sources_used`; a source may have been down-ranked by the trust layer.
- **Stale monitor results** — check the memory layer's snapshot timestamp; monitors run on a schedule, not continuously.
- **Unexpected browser behavior** — see [core/browser-engine.md](../core/browser-engine.md) and [guides/using-browser-workflows.md](../guides/using-browser-workflows.md).

See [concepts/execution-graphs.md](../concepts/execution-graphs.md) for the full model, and [concepts/explainability.md](../concepts/explainability.md) for the philosophy behind it.
