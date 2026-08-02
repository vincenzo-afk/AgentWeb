# Success Metrics

## Product-level

| Metric | Target signal |
|---|---|
| Citation coverage | % of synthesized claims with a valid citation — should approach 100% |
| Source trust calibration | Correlation between `trust_score` and human-rated source reliability on sampled results |
| Memory reuse rate | % of recurring-target requests served (partially or fully) from cache — should trend upward over time |
| Time-to-first-result by mode | p95 latency per [retrieval mode](../../docs/concepts/retrieval-modes.md) within [SLO targets](../../docs/operations/sla-slo.md) |

## Strategic

| Metric | Target signal |
|---|---|
| Skill reuse rate | % of `solve` calls served by a matching [Internet Skill](../../docs/concepts/internet-skills.md) rather than fresh planning |
| Cost per recurring task, over time | Should decline as memory reuse and skill reuse increase (the learning moat — see [docs/research/economic-model.md](../../docs/research/economic-model.md)) |
| Enterprise explainability adoption | % of enterprise accounts actively using execution-graph inspection/audit features |

## Roadmap-level

See [docs/roadmap.md](../../docs/roadmap.md) for phase-gated milestones this rolls up to.
