# Example: Research Agent

Demonstrates using the [Agent APIs](../../docs/concepts/agents.md) to plan, inspect, and execute a multi-step research task, rather than a single opaque `solve()` call.

```js
const plan = await internet.plan({
  task: "Research three emerging competitors to Company X and summarize their funding, product, and hiring signals"
});

console.log(plan.steps); // inspect before running

const result = await internet.execute({ planId: plan.id });
console.log(result.answer);

const trace = await internet.report(result.executionId);
```

Useful when an agent (or a human supervisor) needs to approve or modify a plan before it executes — see [core/planner.md](../../docs/core/planner.md).
