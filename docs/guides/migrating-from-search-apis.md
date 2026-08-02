# Migrating from Search APIs

If you currently call a search API and post-process results yourself (ranking, deduping, summarizing), AgentWeb can typically replace that pipeline with a single call.

## Before

```js
const results = await searchApi.query(q);
const ranked = myRankingLogic(results);
const summary = await llm.summarize(ranked);
```

## After

```js
const result = await internet.solve({ task: q, mode: "focus" });
// result.answer is already ranked, synthesized, and cited
```

## Migration tips

- Start with `mode: "flash"` or `"focus"` for parity with typical search-API latency; move to `"dive"` only where you were previously doing multi-step research manually.
- If you relied on raw search results (not synthesis), use the low-level [`/search`](../api/reference/search.md) endpoint directly instead of `/solve`.
- Replace custom ranking/trust logic with [Custom Rankers](custom-rankers.md) if you need to preserve domain-specific weighting.
