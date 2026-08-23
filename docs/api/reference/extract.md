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
  "source_url": "https://example.com/product/123",
  "confidence": 0.88,
  "field_confidence": { "title": 0.95, "text": 0.85, "links": 0.85 }
}
```

If `schema` is omitted, AgentWeb returns a best-effort normalized extraction (text, metadata, and detected structured fields). Every response includes an overall `confidence` score and `field_confidence` values for the core extracted fields. In schema-guided mode, each normalized field also includes `normalized`, `raw`, and `confidence`; successful deterministic canonicalization receives higher confidence than an unparseable raw value. Parse warnings reduce the overall confidence rather than causing the extraction to fabricate a value.
