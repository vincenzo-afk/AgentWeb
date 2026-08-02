# Economic Model

## Cost drivers

- Retrieval depth (Flash < Focus < Dive < Monitor-per-check) — see [concepts/retrieval-modes.md](../concepts/retrieval-modes.md).
- Browser session usage (rendering + interaction is more expensive than static fetch/search).
- Monitor check frequency and target count.
- Cache/memory reuse rate — higher reuse directly reduces cost for recurring targets.

## The learning moat

The most durable economic advantage is not raw search quality or browser coverage, but accumulated task intelligence: which strategies work best for which problem classes, which sources tend to be trustworthy, which extraction pathways are stable, and how to minimize cost while preserving result quality. As the [Planner](../core/planner.md) reuses successful strategies (formalized as [Internet Skills](../concepts/internet-skills.md)), the marginal cost of serving a recurring task class falls over time while quality holds or improves — a compounding advantage competitors without accumulated run history can't easily replicate.

## Memory as a cost lever

Because the [Memory layer](../concepts/memory-model.md) avoids redundant fetches and re-processing, cost per recurring task (especially monitoring) falls as the reuse rate improves, rather than scaling linearly with check frequency.

See [operations/cost-controls.md](../operations/cost-controls.md) for the customer-facing side of managing spend.
