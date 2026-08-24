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

AgentWeb's local MVP includes built-in `comparison`, `price_lookup`, and `source_summary` templates. A request may select one explicitly through `/solve` with `skill` and `inputs`, or the planner may match a built-in template from task wording. Explicit skill names are validated; unknown names fail closed rather than silently changing strategy. Matching is deterministic, and ties are resolved by historical success rate only when a caller supplies registered skills with equal similarity.

```js
await internet.solve({ skill: "compare-products", inputs: { items: ["A", "B", "C"] } });
```

## Guidelines

- Keep skills narrow and composable rather than trying to cover every variant of a task in one skill.
- Skill templates contain generic metadata and bounded steps only; organization-specific task content is supplied at planning time and is not persisted in the registry.
- The skill registry is available through `/solve` and through the authenticated `/plan` → approval → `/execute` workflow. Plan records are tenant-scoped, expiring, and do not persist task content; the learning loop remains deferred roadmap work.
- Skills that perform well (fast, well-cited, low-cost) for a task class are strong candidates for promotion into the platform's built-in skill library. See [research/economic-model.md](../research/economic-model.md) for why this matters strategically.
