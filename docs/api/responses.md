# Responses

Standard response envelope:

```json
{
  "execution_id": "run_abc123",
  "mode": "dive",
  "answer": "...",
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
- `sources` — evidence used, each with a trust score and citation flag.
- `diff` — present for `observe`/monitor results when a change was detected.

See [citations.md](citations.md) for how claims map to sources, and [errors.md](errors.md) for error responses.
