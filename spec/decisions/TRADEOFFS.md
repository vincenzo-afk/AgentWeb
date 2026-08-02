# Tradeoffs

| Decision | Benefit | Cost |
|---|---|---|
| Outcome-first API as primary surface | Simpler integration, strategy improves without client changes | Less transparency/control by default (mitigated by execution graphs + low-level primitives) |
| Execution graph on every run | Explainability, debuggability, audit | Storage + processing overhead per run |
| Content-addressed snapshots | Reliable diffing, dedup | Slightly more storage than in-place updates |
| Memory-first reuse | Lower cost, faster recurring tasks | Risk of serving slightly stale data if reuse policy is too permissive (mitigated by task-aware freshness windows) |
| Browser as escalation, not default | Lower average cost/latency | Router misclassification risk (page needed rendering but wasn't escalated) — mitigated by Connector-based hints |
| Scope-based (not row-level) authorization | Simpler to reason about and audit | Less granular than per-resource ACLs; acceptable given current API resource model |

See [ASSUMPTIONS.md](ASSUMPTIONS.md) and [CONSTRAINTS.md](CONSTRAINTS.md) for the boundaries these tradeoffs were made within.
