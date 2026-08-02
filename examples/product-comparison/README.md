# Example: Product Comparison

Comparing multiple products across price, availability, and specs — a good fit for a [custom skill](../custom-skill/) once you run this pattern repeatedly.

```js
const result = await internet.solve({
  task: "Compare the RTX 6090, RTX 6080, and RX 8900 XT on price and availability in India, cite sources",
  mode: "dive"
});

console.log(result.answer);
```

For a reusable version of this pattern, see [docs/guides/creating-skills.md](../../docs/guides/creating-skills.md) and the [custom-skill example](../custom-skill/).
