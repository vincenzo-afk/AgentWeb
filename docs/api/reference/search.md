# `POST /search`

Low-level primitive: fast retrieval of web results, links, summaries, and candidate sources. Use directly when you need raw search results without synthesis; most applications should prefer [`/solve`](solve.md).

## Request

```json
{
  "query": "cheapest RTX 6090 India",
  "limit": 10
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | yes | Search query |
| `limit` | integer | no | Max results (default 10, max 50) |
| `freshness` | string | no | `day`, `week`, `month`, `year`, `any` |

## Response

```json
{
  "results": [
    { "url": "https://...", "title": "...", "snippet": "...", "published_at": "2026-07-20T00:00:00Z" }
  ]
}
```
