# Creating Skills

[Internet Skills](../concepts/internet-skills.md) are reusable strategy templates for recurring task classes.

## Define a skill

```json
{
  "name": "compare-products",
  "description": "Compare N products across price, availability, and key specs",
  "input_schema": { "items": "array<string>" },
  "plan_template": {
    "mode": "dive",
    "steps": ["search_each_item", "extract_price_and_specs", "rank_sources", "synthesize_comparison"]
  }
}
```

## Using a skill

```js
await internet.solve({ skill: "compare-products", inputs: { items: ["A", "B", "C"] } });
```

## Guidelines

- Keep skills narrow and composable rather than trying to cover every variant of a task in one skill.
- Skills that perform well (fast, well-cited, low-cost) for a task class are strong candidates for promotion into the platform's built-in skill library. See [research/economic-model.md](../research/economic-model.md) for why this matters strategically.
