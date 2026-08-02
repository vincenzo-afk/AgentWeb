# Example: Custom Skill

Defining a reusable [Internet Skill](../../docs/concepts/internet-skills.md) for a recurring task shape, then invoking it by name.

```js
await internet.skills.create({
  name: "compare-products",
  description: "Compare N products across price, availability, and key specs",
  inputSchema: { items: "array<string>" },
  planTemplate: {
    mode: "dive",
    steps: ["search_each_item", "extract_price_and_specs", "rank_sources", "synthesize_comparison"]
  }
});

const result = await internet.solve({
  skill: "compare-products",
  inputs: { items: ["Product A", "Product B", "Product C"] }
});
```

See [guides/creating-skills.md](../../docs/guides/creating-skills.md) for design guidance on keeping skills narrow and composable.
