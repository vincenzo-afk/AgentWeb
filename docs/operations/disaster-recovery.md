# Disaster Recovery

## Backup strategy

Snapshot, graph, and execution-trace stores are backed up on a schedule consistent with their [retention policy](data-retention.md). Backups are tested periodically via restore drills.

## Failure scenarios

| Scenario | Mitigation |
|---|---|
| Regional infrastructure outage | Multi-region failover for the API layer; in-flight monitors resume on the next scheduled check after recovery |
| Snapshot store corruption/loss | Restore from backup; affected monitors report a gap in diff history rather than false "no change" results |
| Graph store loss | Restore from backup; graph can also be partially rebuilt by replaying retained execution traces where within retention window |
| Downstream webhook receiver outage | Webhook delivery retries with backoff for a bounded window; failures beyond that are surfaced via `/observe/{id}` status rather than silently dropped |

## Recovery objectives (indicative)

- RTO (Recovery Time Objective): platform API restored within a few hours of a regional outage.
- RPO (Recovery Point Objective): bounded by backup frequency for each store; snapshot/graph data may lag by up to the backup interval in a worst-case restore.
