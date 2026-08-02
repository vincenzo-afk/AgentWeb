# Database Schema

## Core tables (relational store — keys, orgs, usage, monitors)

```sql
organizations(id, name, created_at)
api_keys(id, org_id, scope, prefix, hashed_secret, created_at, revoked_at)
runs(id, org_id, task, mode, status, created_at, completed_at)
monitors(id, org_id, task, status, frequency, webhook_url, created_at, last_checked_at, last_change_at)
usage_records(id, org_id, period, mode, count, cost)
```

## Non-relational stores
Snapshots, graph, and execution traces use purpose-built stores rather than the relational schema above — see [STORAGE_SPEC.md](STORAGE_SPEC.md), [ER_DIAGRAM.md](ER_DIAGRAM.md) (for the graph's entity model), and [OBJECT_MODEL.md](OBJECT_MODEL.md).

## Indexing
See [INDEXING.md](INDEXING.md) for indexes required on `runs`, `monitors`, and `usage_records` to support the query patterns in [../../docs/api/filtering.md](../../docs/api/filtering.md).
