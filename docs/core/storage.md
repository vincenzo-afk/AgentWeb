# Storage

Underlying storage systems supporting the platform's layers.

| Store | Backs | Notes |
|---|---|---|
| Snapshot store | [Memory](memory.md) | Content-addressed by hash; supports diffing and historical replay; every record is organization-scoped |
| Graph store | [Knowledge Graph](knowledge-graph.md) | Entity/relationship storage supporting multi-hop queries |
| Execution trace store | [Observability](observability.md) | Append-only trace records assembled into execution graphs and filtered by organization ownership |
| Skill/plan store | [Planner](planner.md) | Reusable strategy templates and cached successful plans |
| Key/usage store | [Admin](../api/reference/admin.md) | Organization-scoped hashed API keys, scopes, audit events, and usage/billing records |

Monitor, webhook, and `retention_gc` jobs are persisted in the same SQLite deployment with organization ownership, leases, retries, and dead-letter state. Crawl runs and page metadata share the local memory boundary, and retention cleanup removes expired crawl records together with their pages. Every ownership-sensitive read, update, delete, and job claim includes the organization boundary. Optional PostgreSQL queue mode coordinates retention-job leases without implying a full relational business-record cutover. See [security/data-privacy.md](../security/data-privacy.md) for handling of third-party page content within these stores, and [operations/data-retention.md](../operations/data-retention.md) for retention policy.
