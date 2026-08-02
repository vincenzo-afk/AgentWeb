# Source Trust Tuning

Tune how the [Trust Model](../concepts/trust-model.md) weighs sources for your domain.

## Options

- **Domain boosts/penalties** — per-request or organization-level (see [Custom Rankers](custom-rankers.md)).
- **Source-type preferences** — e.g., prefer primary sources (official docs, regulatory filings) over aggregators for compliance-sensitive tasks.
- **Recency weighting** — increase the penalty for stale sources on fast-moving topics (pricing, availability) vs. more stable topics (historical facts).

## Inspecting current behavior

```js
const result = await internet.solve({ task: "..." });
console.log(result.sources.map(s => ({ url: s.url, trust_score: s.trust_score, cited: s.cited })));
```

Iterate by adjusting overrides and re-running against representative tasks; compare `trust_score` distributions before/after.
