# Custom Rankers

Advanced users can supply domain-specific ranking logic layered on top of the default [Trust Model](../concepts/trust-model.md) — for example, weighting internal/enterprise documentation above public web results, or preferring regulatory/primary sources for compliance-sensitive tasks.

## Approach

1. Provide a ranking override: a list of domains/source types with weight adjustments, or a scoring function for more advanced cases.
2. Apply it per-request (`ranker: "my-ranker"`) or as an organization-level default.
3. Inspect the effect via `trust_scores` in the response and the [execution graph](../concepts/execution-graphs.md).

## Example

```json
{
  "task": "...",
  "ranker_overrides": {
    "boost_domains": ["docs.internal.example.com"],
    "penalize_domains": ["random-forum.example.com"]
  }
}
```

See [core/ranking.md](../core/ranking.md) for the underlying mechanism.
