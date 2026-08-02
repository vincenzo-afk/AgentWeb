# Deployment Architecture

## Deployable units

- **API tier** — stateless, horizontally scaled behind a load balancer.
- **Orchestration tier** (Planner/Router) — stateless, scaled with request volume.
- **Execution workers** (Search/Crawl/Browser/Extract) — scaled independently per primitive; Browser workers are the most resource-intensive (see [../scaling/RESOURCE_LIMITS.md](../scaling/RESOURCE_LIMITS.md)) and isolated per [../security/SECURITY_MODEL.md](../security/SECURITY_MODEL.md) sandboxing requirements.
- **Memory/Graph stores** — durable, replicated data stores; see [../data/STORAGE_SPEC.md](../data/STORAGE_SPEC.md).
- **Job scheduler** — drives Monitor checks and async work; see [../data/QUEUE_SPEC.md](../data/QUEUE_SPEC.md).
- **Observability pipeline** — ingests traces/metrics/logs from all tiers.

## Multi-region considerations

API tier deployed multi-region for availability (see [../../docs/operations/disaster-recovery.md](../../docs/operations/disaster-recovery.md)); execution workers may be deployed closer to target geographies to reduce latency for region-specific browsing/extraction.
