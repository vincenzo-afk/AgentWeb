# Observability

Every run produces an [execution graph](../concepts/execution-graphs.md): a full record of planning, actions, and decisions. This document covers how that's implemented internally.

## Components

- **Trace collection** — every planner decision, router selection, tool call, memory lookup, and synthesis step is logged with timing and inputs/outputs.
- **Execution graph assembly** — traces are assembled into a structured graph retrievable via [`/report/{execution_id}`](../api/reference/agents.md).
- **Historical replay projection** — the read-only [`/report/{execution_id}/replay`](../api/reference/agents.md) route converts a tenant-authorized persisted trace into ordered nodes and edges with sanitized summaries and timing. It explicitly performs no network re-execution and no side effects.
- **Metrics** — latency, cost, and cache-hit-rate (memory reuse) per run, aggregated for [operations/monitoring-stack.md](../operations/monitoring-stack.md) and [admin usage reporting](../api/reference/admin.md).

## Retention

Execution graph retention follows [operations/data-retention.md](../operations/data-retention.md); longer retention supports audit/replay use cases described in [guides/enterprise-rollout.md](../guides/enterprise-rollout.md).
