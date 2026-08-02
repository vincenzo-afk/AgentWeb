# `GET /graph/query`

Direct access to the knowledge graph layer (post-MVP; see [roadmap.md](../../roadmap.md) Phase 2). Supports entity and relationship queries across evidence gathered by prior runs and monitors.

## Request

```
GET /graph/query?entity_type=company&related_to=Company+X&relation=competitor
```

## Response

```json
{
  "nodes": [ { "id": "ent_1", "type": "company", "name": "Company Y" } ],
  "edges": [ { "from": "ent_1", "to": "ent_x", "type": "competitor", "confidence": 0.8 } ]
}
```

See [concepts/knowledge-model.md](../../concepts/knowledge-model.md), [core/knowledge-graph.md](../../core/knowledge-graph.md), and [guides/graph-powered-research.md](../../guides/graph-powered-research.md).
