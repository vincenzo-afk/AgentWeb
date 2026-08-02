# ER Diagram

## Knowledge graph entity-relationship model

```
Entity (id, type, name, first_seen_at, last_updated_at)
   type ∈ { company, person, product, release, funding_event, page, org }

Relation (id, from_entity_id, to_entity_id, type, confidence, first_seen_at, last_confirmed_at)
   type ∈ { competitor, founder_of, launched_by, funded_by, mentions, depends_on }

Source (id, url, first_seen_at, trust_score)

EntitySource (entity_id, source_id)   -- provenance: which sources support this entity
RelationSource (relation_id, source_id) -- provenance: which sources support this relation
```

Every entity and relation must trace to at least one `Source` record — this is what makes graph query results explainable per [docs/concepts/explainability.md](../../docs/concepts/explainability.md). See [../module-specs/GRAPH_SPEC.md](../module-specs/GRAPH_SPEC.md) for the query interface over this model.
