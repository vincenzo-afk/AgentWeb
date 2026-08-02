# Response Schema

See [schemas/solve-response.schema.json](../../schemas/solve-response.schema.json) and [schemas/monitor.schema.json](../../schemas/monitor.schema.json) for machine-readable versions, and [docs/api/responses.md](../../docs/api/responses.md) for the prose version.

## Standard envelope
```json
{
  "execution_id": "string",
  "mode": "flash|focus|dive",
  "answer": "string",
  "sources": [{ "id": "string", "url": "string", "trust_score": "number", "cited": "boolean" }],
  "citations": [{ "claim_span": [0, 0], "source_ids": ["string"] }],
  "created_at": "ISO 8601 timestamp"
}
```

## Consistency rule
Every field present in a successful response must be non-null; optional data that wasn't gathered (e.g., no graph context available) should omit the field rather than return `null`, to keep client-side parsing simple.
