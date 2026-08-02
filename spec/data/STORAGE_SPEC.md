# Storage Spec

See [docs/core/storage.md](../../docs/core/storage.md) for the conceptual overview. Build-level detail:

| Store | Type | Key | Notes |
|---|---|---|---|
| Snapshot store | Content-addressed blob store | `hash(target + content)` | Supports diffing; see [MEMORY_SPEC](../module-specs/MEMORY_SPEC.md) |
| Graph store | Graph database | `entity_id` / `relation_id` | Supports multi-hop traversal queries |
| Execution trace store | Append-only log store | `execution_id` | Optimized for write-once, read-by-id |
| Relational store | RDBMS | per [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Orgs, keys, runs, monitors, usage |
| Cache | In-memory KV | varies | See [CACHE_SPEC.md](CACHE_SPEC.md) |

## Consistency
Snapshot writes are immutable once created (new content = new hash, not an update); this is what makes historical replay reliable.
