# `POST /search`

Low-level primitive: fast retrieval of web results, links, summaries, and candidate sources. Use directly when you need raw search results without synthesis; most applications should prefer [`/solve`](solve.md).

## Request

```json
{
  "query": "cheapest RTX 6090 India",
  "limit": 10,
  "freshness": "month"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | yes | Search query |
| `limit` | integer | no | Max results (default 10, max 50) |
| `freshness` | string | no | `day`, `week`, `month`, `year`, `any`; forwarded to configured providers when supported |

## Response

```json
{
  "results": [
    { "url": "https://...", "title": "...", "snippet": "...", "published_at": "2026-07-20T00:00:00Z" }
  ]
}
```

The default provider is the free DuckDuckGo HTML adapter. Set `AGENTWEB_SEARCH_PROVIDER=json` and `AGENTWEB_SEARCH_ENDPOINT` to use an HTTP JSON provider that returns either a result array or `{ "results": [...] }`; `AGENTWEB_SEARCH_API_KEY` is resolved through the external secret boundary when present. If a configured JSON provider fails, AgentWeb falls back to DuckDuckGo and returns an empty list only when both providers are unavailable. Provider credentials and response bodies are never written to traces.
