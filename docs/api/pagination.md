# Pagination

List endpoints such as `/observe`, `/memory/{target}`, `/admin/keys`, and `/admin/audit` use cursor-based pagination. Graph query pagination remains deferred with the graph feature.

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

Avoid relying on offset-based pagination assumptions; always use the returned `next_cursor`.
