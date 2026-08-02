# Execution Graphs

Every AgentWeb run produces an inspectable **execution graph**: a full record of the plan and actions taken, including planning decisions, searches performed, browser sessions opened, extraction steps, memory lookups, graph updates, ranking decisions, and synthesis steps.

Execution graphs support:

- **Debugging** complex internet workflows
- **Replaying or auditing** prior runs
- **Enterprise trust and observability**
- **Strategy optimization and learning** over time (identifying which plans worked well)

```js
const trace = await internet.report(execution_id);
console.log(trace.plan);
console.log(trace.actions);
console.log(trace.sources_used);
```

See [getting-started/debugging-basics.md](../getting-started/debugging-basics.md) for a hands-on walkthrough and [core/observability.md](../core/observability.md) for the underlying implementation.
