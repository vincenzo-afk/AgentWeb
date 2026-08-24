# Observability

Every run produces an [execution graph](../concepts/execution-graphs.md): a full record of planning, actions, and decisions. This document covers how that's implemented internally.

## Components

- **Trace collection** — every planner decision, router selection, tool call, memory lookup, and synthesis step is logged with timing and inputs/outputs.
- **Execution graph assembly** — traces are assembled into a structured graph retrievable via [`/report/{execution_id}`](../api/reference/agents.md).
- **Historical replay projection** — the read-only [`/report/{execution_id}/replay`](../api/reference/agents.md) route converts a tenant-authorized persisted trace into ordered nodes and edges with sanitized summaries and timing. It explicitly performs no network re-execution and no side effects.
- **Metrics** — latency, cost, and cache-hit-rate (memory reuse) per run, aggregated for [operations/monitoring-stack.md](../operations/monitoring-stack.md) and [admin usage reporting](../api/reference/admin.md).
- **Structured logging** — the API emits one bounded JSON record per request with a UTC timestamp, level, component, request correlation ID, method, redacted target, and status code. `AGENTWEB_QUIET=1` disables request log emission for local probes.

## Logging safety

Log records are diagnostic summaries, not a content store. URL credentials and credential-like query values are redacted, common token/password/secret representations are removed, and sensitive extra fields such as request bodies, cookies, credentials, and page content are dropped. Full page bodies must never be passed to the logger; use a content hash or reference when a diagnostic needs to identify a payload.

## Retention

Execution graph retention follows [operations/data-retention.md](../operations/data-retention.md); longer retention supports audit/replay use cases described in [guides/enterprise-rollout.md](../guides/enterprise-rollout.md).
