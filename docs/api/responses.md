# Responses

AgentWeb keeps endpoint-specific success payloads stable and adds a reserved `_meta` object to every successful JSON object response. This is additive response-envelope parity: existing top-level fields such as `execution_id`, `data`, `sources`, `pages`, and deletion counts remain available at their current locations. A response is not wrapped in a new `data` container.

## Success metadata

```json
{
  "status": "ok",
  "service": "agentweb",
  "checks": {"memory": "ok", "metrics": "ok", "audit": "ok", "queue": "disabled"},
  "_meta": {
    "request_id": "req_abc123",
    "api_version": "v1",
    "path": "/v1/health",
    "deprecated": false
  }
}
```

The `_meta` object contains the request-scoped identifier echoed by the `X-Request-ID` header, the canonical API version, the canonical `/v1` path, and whether the request used the deprecated bare-path compatibility bridge. Versioned requests have `deprecated: false`; equivalent unversioned requests have `deprecated: true` and return `Deprecation: true`.

The server also returns `X-AgentWeb-API-Version: v1` on JSON and no-content responses. A `204 No Content` response has no body and therefore has no `_meta` object. Its headers still carry the API version and, when applicable, request and deprecation metadata.

## Standard solve payload

The solve response remains an endpoint-specific standard payload with additive metadata:

```json
{
  "execution_id": "run_abc123",
  "mode": "dive",
  "answer": "...",
  "output_format": "text",
  "evidence_score": 0.82,
  "conflicts": [],
  "insufficient_evidence": false,
  "sources": [
    { "url": "https://...", "trust_score": 0.87, "cited": true }
  ],
  "created_at": "2026-07-31T12:00:00Z",
  "_meta": {
    "request_id": "req_abc123",
    "api_version": "v1",
    "path": "/v1/solve",
    "deprecated": false
  }
}
```

## Fields

- `_meta` — additive request and API metadata; it is reserved by AgentWeb and is not a replacement for endpoint fields.
- `execution_id` — unique identifier for the run; use with [`/report`](reference/admin.md) to inspect the execution graph.
- `mode` — the retrieval mode actually used.
- `answer` — synthesized, cited output (present for `solve`).
- `output_format` — the selected deterministic rendering: `text`, `comparison`, `timeline`, or `json`.
- `evidence_score` — bounded local score derived from included ranked-source quality and evidence coverage.
- `conflicts` — detected disagreements, including the field and source observations; an empty array means none were detected.
- `insufficient_evidence` — true when selected evidence is empty or below the synthesis threshold; no unsupported citation is emitted in that case.
- `structured_output` — machine-readable output for the `json`, `comparison`, or `timeline` formats.
- `sources` — evidence considered, each with a trust score, citation flag, optional publication time, content type, extraction confidence, and bounded `structured_data` containing extracted tables and entities when available.
- `citations` — line-level claim spans mapped to one or more source IDs; spans use zero-based offsets into `answer`.
- `diff` — present for `observe`/monitor results when a change was detected.
- Extraction responses additionally expose `tables`, `entities`, and `source_spans`; source spans are local offsets into the returned title or text field.
- Crawl responses expose a durable `crawl_id`, bounded page metadata, `pages_crawled`, and `truncated`; `GET /crawl` and `GET /crawl/{id}` return only the authenticated organization’s history.
- Browser session-state lifecycle responses expose only opaque IDs, labels, normalized origins, timestamps, and revocation metadata. They never expose cookies, local-storage values, or session tokens.
- `DELETE /admin/data` returns deletion counts for snapshots, crawl history, browser session states, and traces owned by the authenticated organization. It does not delete API keys, audit events, or usage records.
- `GET /admin/metrics` returns organization-filtered counters, observations, and gauges. Authenticated responses expose `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`; a `429` response also exposes `Retry-After`.

## Idempotent responses

An idempotent mutation stores the endpoint result, not a new business operation. A replay preserves the original endpoint-specific fields and status code, but receives a new request-scoped `request_id` in `_meta` and `X-Request-ID`. This keeps request correlation correct while ensuring the replay does not create a second solve, monitor, crawl, key, or credential.

## Errors

Error responses retain the existing stable shape and do not receive a success `_meta` object:

```json
{
  "error": {
    "type": "invalid_request",
    "message": "task must contain between 1 and 2000 characters",
    "request_id": "req_abc123"
  }
}
```

See [citations.md](citations.md) for how claims map to sources and [errors.md](errors.md) for error status/type mappings.
