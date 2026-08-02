# Ranking

The ranking/trust layer scores sources and evidence quality before synthesis, determining which gathered evidence actually contributes to the final answer.

## Signals

- Source reputation/historical reliability
- Corroboration across independent sources
- Recency relative to the task
- Content-type appropriateness (primary source vs. aggregator vs. forum)
- Extraction confidence (how reliably structured data was pulled from the page)

## Output

Each source receives a `trust_score` and a `cited` flag once synthesis completes (see [api/citations.md](../api/citations.md)). Domain-specific tuning is available; see [guides/source-trust-tuning.md](../guides/source-trust-tuning.md).

## Custom rankers

Advanced users can supply custom ranking logic for their domain (e.g., weighting internal/enterprise sources higher). See [guides/custom-rankers.md](../guides/custom-rankers.md).
