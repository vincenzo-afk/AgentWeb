# Responses

Standard response envelope:

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
  "created_at": "2026-07-31T12:00:00Z"
}
```

## Fields

- `execution_id` — unique identifier for the run; use with [`/report`](reference/admin.md) to inspect the execution graph.
- `mode` — the retrieval mode actually used.
- `answer` — synthesized, cited output (present for `solve`).
- `output_format` — the selected deterministic rendering: `text`, `comparison`, `timeline`, or `json`.
- `evidence_score` — bounded local score derived from included ranked-source quality and evidence coverage.
- `conflicts` — detected disagreements, including the field and source observations; an empty array means none were detected.
- `insufficient_evidence` — true when selected evidence is empty or below the synthesis threshold; no unsupported citation is emitted in that case.
- `structured_output` — machine-readable output for the `json`, `comparison`, or `timeline` formats.
- `sources` — evidence considered, each with a trust score, citation flag, optional publication time, content type, and extraction confidence.
- `citations` — line-level claim spans mapped to one or more source IDs; spans use zero-based offsets into `answer`.
- `diff` — present for `observe`/monitor results when a change was detected.
- Extraction responses additionally expose `tables`, `entities`, and `source_spans`; source spans are local offsets into the returned title or text field.
- `DELETE /admin/data` returns deletion counts for snapshots and traces owned by the authenticated organization. It does not delete API keys, audit events, or usage records.
- `GET /admin/metrics` returns organization-filtered counters, observations, and gauges. Authenticated responses expose `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`; a `429` response also exposes `Retry-After`.

See [citations.md](citations.md) for how claims map to sources, and [errors.md](errors.md) for error responses.
