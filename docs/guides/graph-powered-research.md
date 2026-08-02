# Graph-Powered Research

Once the [Knowledge Graph](../core/knowledge-graph.md) layer is available for your organization (see [roadmap.md](../roadmap.md) Phase 2), you can query relationships directly rather than only asking one-off synthesis questions.

## Example: competitor discovery

```js
const graph = await internet.graph.query({
  entity_type: "company",
  related_to: "Company X",
  relation: "competitor"
});
```

## Example: combining graph + solve

```js
const competitors = await internet.graph.query({ related_to: "Company X", relation: "competitor" });
const report = await internet.solve({
  task: `Summarize recent funding and product activity for: ${competitors.nodes.map(n => n.name).join(", ")}`
});
```

Graph queries are strongest for relationship-heavy questions (who competes with whom, what depends on what) that plain search struggles to answer; use [`/solve`](../api/reference/solve.md) for narrative synthesis once relevant entities are identified.
