# Knowledge graph

AgentWeb exposes a tenant-scoped knowledge graph for storing normalized entities and relationships observed across independent sources. Graph writes require `graph:write`; reads require `graph:read`. Every response includes the standard `_meta` object on canonical `/v1` paths.

## Upsert an entity

```http
POST /v1/graph/entities
Content-Type: application/json

{
  "type": "Company",
  "name": "Acme",
  "attributes": {"sector": "manufacturing"},
  "confidence": 0.8,
  "source_ids": ["src_abc"]
}
```

Entities are deduplicated within an organization by case-insensitive `(type, name)`. Subsequent observations merge attributes and source IDs without exposing data from another organization.

## Upsert a relation

```http
POST /v1/graph/relations
Content-Type: application/json

{
  "from_id": "ent_company",
  "to_id": "ent_product",
  "relation": "produces",
  "confidence": 0.75,
  "source_ids": ["src_abc", "src_xyz"]
}
```

Both endpoints accept an `Idempotency-Key` header. Relation observations are merged by `(from_id, to_id, relation)` and retain an observation count and independent source IDs.

## Query the graph

```http
GET /v1/graph/query?entity_type=Company&related_to=ent_company&relation=produces&limit=50
```

All query parameters are optional. Results contain endpoint nodes and matching edges. Edge confidence is adjusted upward for independent source corroboration and gently discounted as an edge becomes stale; historical edges are retained rather than deleted.

```json
{
  "nodes": [
    {
      "id": "ent_company",
      "type": "Company",
      "name": "Acme",
      "attributes": {},
      "confidence": 0.8,
      "source_ids": []
    }
  ],
  "edges": [
    {
      "id": "rel_123",
      "from": "ent_company",
      "to": "ent_product",
      "relation": "produces",
      "confidence": 0.84,
      "source_ids": ["src_abc", "src_xyz"],
      "observations": 2
    }
  ]
}
```

See [concepts/knowledge-model.md](../../concepts/knowledge-model.md), [core/knowledge-graph.md](../../core/knowledge-graph.md), and [guides/graph-powered-research.md](../../guides/graph-powered-research.md).
