# `POST /extract`

Low-level primitive: transforms a raw page (or previously fetched/crawled/browsed content) into structured output — text, metadata, tables, lists, entities, prices, dates, links, summaries, normalized content.

## Request

```json
{
  "url": "https://example.com/product/123",
  "schema": {
    "price": "number",
    "availability": "string",
    "title": "string"
  }
}
```

## Response

```json
{
  "data": { "price": 42999, "availability": "in_stock", "title": "RTX 6090" },
  "source_url": "https://example.com/product/123"
}
```

If `schema` is omitted, AgentWeb returns a best-effort normalized extraction (text, metadata, and detected structured fields).
