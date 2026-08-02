# Internet Skills

Internet Skills are reusable workflows or strategy templates for recurring classes of tasks. Instead of planning every request from scratch, the platform can expose higher-level capabilities such as:

- Compare products
- Research a company
- Monitor a competitor
- Summarize release notes
- Track visa slots
- Watch GitHub releases
- Detect policy or pricing changes

Skills act as a bridge between generic orchestration and domain-specific outcomes: they encode the planning and execution pattern that already worked well for a task class, so future similar requests don't have to be planned from first principles.

```js
const result = await internet.solve({
  skill: "compare-products",
  inputs: { items: ["Product A", "Product B", "Product C"] }
});
```

See [guides/creating-skills.md](../guides/creating-skills.md) for how to define a custom skill, and [research/economic-model.md](../research/economic-model.md) for why skills contribute to AgentWeb's long-term learning moat.
