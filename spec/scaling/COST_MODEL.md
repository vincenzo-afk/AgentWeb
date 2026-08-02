# Cost Model

## Internal cost drivers, by primitive
- **Browser** — highest per-call cost (compute + isolation overhead); dominant driver of `dive`-mode and Browser-heavy monitor cost.
- **Search** — lowest per-call cost; dominant driver of `flash` mode.
- **Extraction** — moderate, scales with content size and schema complexity.
- **Graph updates** — amortized across many runs since a single update can serve many future queries.
- **Storage** (snapshot/graph/trace) — ongoing cost proportional to retention window and reuse rate (lower reuse → more redundant storage growth).

## Margin model
Price tiers (see [../product/BUSINESS_REQUIREMENTS.md](../product/BUSINESS_REQUIREMENTS.md)) are set against blended cost per mode, with memory reuse rate as the primary lever for improving margin on recurring workloads over time — consistent with [../../docs/research/economic-model.md](../../docs/research/economic-model.md).

## Customer-facing view
See [../../docs/operations/cost-controls.md](../../docs/operations/cost-controls.md).
