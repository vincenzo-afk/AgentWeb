# Graph Spec

## Purpose
Store and query entities/relationships extracted across runs. See [docs/core/knowledge-graph.md](../../docs/core/knowledge-graph.md) and [docs/api/reference/graph.md](../../docs/api/reference/graph.md).

## Interface
```
upsert_entity(entity: Entity) -> EntityId
upsert_relation(from: EntityId, to: EntityId, type: string, confidence: float) -> void
query(entity_type?: string, related_to?: EntityId, relation?: string) -> GraphResult
```

## Data model
See [../data/ER_DIAGRAM.md](../data/ER_DIAGRAM.md) for the entity-relationship schema.

## Confidence and corroboration
Edge confidence increases with independent-source corroboration and recency; single-source, stale edges are down-weighted in query results but not deleted, preserving historical traceability.

## Status
Implemented as an initial bounded local-first Phase 2 slice. Tenant-scoped storage, provenance, corroboration-aware confidence, bounded multi-hop queries, name anchors, graph-assisted solve context, ingestion, and cursor pagination are covered by runtime tests. Calibrated graph quality and general availability remain evaluation/deployment work (see [docs/roadmap.md](../../docs/roadmap.md) Phase 2).
