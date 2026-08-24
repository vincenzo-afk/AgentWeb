# Response Schema

See [schemas/solve-response.schema.json](../../schemas/solve-response.schema.json) and [schemas/monitor.schema.json](../../schemas/monitor.schema.json) for machine-readable endpoint payloads, and [docs/api/responses.md](../../docs/api/responses.md) for the public response reference.

## Additive success metadata

Every successful JSON object response includes the reserved `_meta` object below in addition to its endpoint-specific top-level fields:

```json
{
  "_meta": {
    "request_id": "req_abc123",
    "api_version": "v1",
    "path": "/v1/solve",
    "deprecated": false
  }
}
```

`request_id` is also returned in the `X-Request-ID` response header. `api_version` is currently `v1`. `path` is the canonical `/v1` route even when a bare compatibility path was used. `deprecated` is `true` only for bare routes such as `/solve`; those responses also include `Deprecation: true`.

The metadata is additive rather than a wrapper: AgentWeb does not move existing endpoint fields under `data`, and clients can continue reading fields such as `execution_id`, `answer`, `data`, `sources`, `pages`, and deletion counts at their existing locations. The reserved `_meta` key is overwritten by the API metadata writer if encountered in an object response.

## Standard solve payload

```json
{
  "execution_id": "string",
  "mode": "flash|focus|dive",
  "answer": "string",
  "sources": [{ "id": "string", "url": "string", "trust_score": "number", "cited": "boolean" }],
  "citations": [{ "claim_span": [0, 0], "source_ids": ["string"] }],
  "created_at": "ISO 8601 timestamp",
  "_meta": {
    "request_id": "string",
    "api_version": "v1",
    "path": "/v1/solve",
    "deprecated": "boolean"
  }
}
```

## Consistency rules

Every field present in a successful response must be non-null; optional data that was not gathered should be omitted rather than returned as `null`, except where an endpoint contract explicitly uses nullable values. Successful JSON object responses include `_meta`; `204 No Content` responses have no body and therefore no `_meta` object. Errors retain the stable `{ "error": { "type", "message", "request_id" } }` shape and do not include success metadata.

Idempotent replays preserve the original endpoint-specific payload and status, but receive a new request-scoped `request_id` in `_meta` and `X-Request-ID`.
