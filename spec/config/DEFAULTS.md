# Defaults

| Setting | Default |
|---|---|
| Retrieval mode (when unspecified) | Planner-selected based on task classification |
| Monitor frequency (when unspecified) | `hourly` |
| Search result limit | 10 |
| Crawl max pages | 50 |
| Crawl depth | 2 |
| Snapshot reuse freshness window | Task-type dependent; see [../module-specs/MEMORY_SPEC.md](../module-specs/MEMORY_SPEC.md) reuse policy |
| Webhook retry attempts | 5, exponential backoff (see [../resilience/RETRY_POLICY.md](../resilience/RETRY_POLICY.md)) |
| Browser action timeout | 30s per action (see [../resilience/TIMEOUT_POLICY.md](../resilience/TIMEOUT_POLICY.md)) |
| Execution trace retention | 30 days |
| Snapshot retention | 90 days |
