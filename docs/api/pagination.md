# Pagination

List endpoints (e.g., listing monitors, listing graph query results) use cursor-based pagination.

```json
{
  "data": [ /* ... */ ],
  "next_cursor": "eyJvZmZzZXQiOjEwMH0=",
  "has_more": true
}
```

Request the next page with:

```
GET /observe?cursor=eyJvZmZzZXQiOjEwMH0=
```

Avoid relying on offset-based pagination assumptions; always use the returned `next_cursor`.
