# Jobs

Background job types that drive asynchronous and scheduled work across the platform.

| Job type | Triggered by | Purpose |
|---|---|---|
| `solve_run` | `/solve` | Executes a full plan for a one-shot task |
| `monitor_check` | Scheduler, per active monitor | Performs a scheduled check and diff for [Monitoring](monitoring.md) |
| `webhook_delivery` | Change detection / run completion | Delivers signed payloads to configured webhook URLs |
| `graph_update` | Extraction/synthesis completion | Applies new entities/relationships to the [Knowledge Graph](knowledge-graph.md) |
| `snapshot_gc` | Retention policy | Prunes snapshots beyond the configured retention window |

Jobs are retried with backoff on transient failures (e.g., a target site being temporarily unreachable) and surfaced in the [execution graph](../concepts/execution-graphs.md) when relevant to a specific run.
