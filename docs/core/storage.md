# Storage

Underlying storage systems supporting the platform's layers.

| Store | Backs | Notes |
|---|---|---|
| Snapshot store | [Memory](memory.md) | Content-addressed by hash; supports diffing and historical replay |
| Graph store | [Knowledge Graph](knowledge-graph.md) | Entity/relationship storage supporting multi-hop queries |
| Execution trace store | [Observability](observability.md) | Append-only trace records assembled into execution graphs |
| Skill/plan store | [Planner](planner.md) | Reusable strategy templates and cached successful plans |
| Key/usage store | [Admin](../api/reference/admin.md) | API keys, scopes, usage/billing records |

See [security/data-privacy.md](../security/data-privacy.md) for handling of third-party page content within these stores, and [operations/data-retention.md](../operations/data-retention.md) for retention policy.
