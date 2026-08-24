# Pagination

List endpoints such as `/observe`, `/memory/{target}`, `/admin/keys`, `/admin/audit`, and `/graph/query` use cursor-based pagination. Graph query cursors page the deterministically ordered edge set while returning both endpoint nodes for each page.

```json
{
  "data": [ /* ... */ ],
  "next_cursor": "eyJvZmZzZXQiOjEwMH0=",
  "has_more": true
}
```

The first request may include `limit` from 1 through 100. The response returns the compatibility field for the resource plus the standard `data`, `next_cursor`, and `has_more` fields. Request the next page with:

```
GET /observe?cursor=eyJvZmZzZXQiOjEwMH0=
```

For graph queries, preserve the original filters and request the returned cursor, for example `GET /graph/query?limit=25&entity_type=Company&cursor=eyJvZmZzZXQiOjI1fQ==`. Cursors are opaque; do not construct or modify them manually.

Avoid relying on offset-based pagination assumptions; always use the returned `next_cursor`.
