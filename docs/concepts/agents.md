# Agents

AgentWeb is designed to serve both human-facing applications and autonomous AI agents directly. For agents, single-shot retrieval isn't enough — agents need to plan multi-step work, observe results, react to changes, and produce inspectable output for downstream review.

Agent-native primitives (see [api/reference/agents.md](../api/reference/agents.md)):

```js
await internet.plan(task)     // produce a plan without executing it
await internet.execute(plan)  // execute a previously produced plan
await internet.observe(plan)  // set up recurring observation
await internet.diff(target)   // compute change since last known state
await internet.report(run)    // retrieve the full execution graph
```

These abstractions support inspectability, replay, and intervention: an agent (or its supervisor) can inspect a plan before executing it, or replay a run to understand why a particular action was taken. This is part of the longer-term direction described in [roadmap.md](../roadmap.md) (Phase 3) and complements the general [Execution Graphs](execution-graphs.md) model.
