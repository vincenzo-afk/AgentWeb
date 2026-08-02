# Filtering

List and query endpoints support filtering via query parameters.

```
GET /observe?status=active&created_after=2026-01-01
GET /graph/query?entity_type=company&related_to=Company+X
```

Common filter parameters:

| Param | Applies to | Description |
|---|---|---|
| `status` | monitors | `active`, `paused`, `cancelled` |
| `created_after` / `created_before` | most list endpoints | ISO 8601 timestamps |
| `mode` | run history | filter by retrieval mode used |
| `entity_type` | graph queries | filter by node type (company, product, release, etc.) |

Combine filters with standard `&` query-string syntax; see [reference/graph.md](reference/graph.md) for graph-specific filter syntax.
