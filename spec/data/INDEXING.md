# Indexing

## Relational store indexes

```sql
CREATE INDEX idx_runs_org_created ON runs(org_id, created_at);
CREATE INDEX idx_monitors_org_status ON monitors(org_id, status);
CREATE INDEX idx_usage_org_period ON usage_records(org_id, period);
```

## Snapshot store indexing
Indexed by `target` (for retrieving history of a given URL/entity) and by `hash` (for direct content lookup/dedup across targets that happen to share content).

## Graph store indexing
Indexed by `entity_type`, and by `(from_entity_id, relation_type)` / `(to_entity_id, relation_type)` to support the multi-hop query patterns in [../module-specs/GRAPH_SPEC.md](../module-specs/GRAPH_SPEC.md).

## Vector index
See [VECTOR_STORE.md](VECTOR_STORE.md) for semantic-similarity indexing (skill matching, entity resolution).
