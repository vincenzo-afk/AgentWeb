# Example: Company Analysis

Deep, cited company research using `dive` mode.

```js
const result = await internet.solve({
  task: "Research Company Y: funding history, leadership, recent product launches, and competitive position",
  mode: "dive"
});

console.log(result.answer);
result.sources.filter(s => s.cited).forEach(s => console.log(s.url, s.trustScore));
```

See [guides/citations-in-your-app.md](../../docs/guides/citations-in-your-app.md) for rendering the cited sources in a UI.
