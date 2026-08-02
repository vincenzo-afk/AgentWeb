# Trust Model

Because AgentWeb's outputs are used for decisions, monitoring, research, and compliance-sensitive tasks, source and evidence quality must be explicit rather than implicit.

The ranking/trust layer scores each candidate source before synthesis, based on signals such as:

- Source reputation and historical reliability
- Corroboration across independent sources
- Recency and relevance to the task
- Content-type appropriateness (e.g., primary source vs. aggregator)

Every result exposes:

- `trust_scores` per source
- `sources_considered` vs. `sources_used` (what was seen vs. what made it into the answer)
- Rationale signals where available

```js
console.log(result.sources.map(s => ({ url: s.url, trust_score: s.trust_score })));
```

Developers building on AgentWeb can also tune trust behavior for their domain — see [guides/source-trust-tuning.md](../guides/source-trust-tuning.md) and the implementation details in [core/ranking.md](../core/ranking.md) and [core/trust-and-safety.md](../core/trust-and-safety.md).
