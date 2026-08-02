# Edge Cases

- **Empty or near-empty search results** for a valid but obscure task — Synthesis should return a low-confidence answer with `insufficient_evidence: true` rather than fabricating content.
- **Task description is ambiguous or underspecified** — Planner defaults to a conservative plan and mode rather than guessing an expansive, costly strategy.
- **Duplicate/near-duplicate sources** (mirrors, syndicated content) — Ranking should avoid over-counting corroboration from sources that are actually copies of one another.
- **Monitor target's structure changes entirely** (e.g., a page redesign) — Memory's diff should flag this as a large structural change rather than reporting spurious granular "changes" across every field.
- **Idempotency key reused with a semantically-identical but not byte-identical payload** (e.g., different key ordering) — normalize payloads before comparison to avoid false `409 conflict` responses.
- **Skill input doesn't match `input_schema` exactly** but is close (e.g., extra fields) — accept and ignore extras rather than rejecting, unless strict mode is requested.

See [FAILURE_MODES.md](FAILURE_MODES.md) for outright failures and [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) for cases we accept as out of scope rather than solve.
