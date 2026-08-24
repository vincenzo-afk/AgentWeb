# Agent APIs

Endpoints designed for autonomous agents that need to plan, execute, observe, and audit multi-step internet work independently (see [roadmap.md](../../roadmap.md) Phase 3).

## `POST /plan`

Produces a plan without executing it, for inspection or approval before running. The route requires `solve:execute`. Plans are held in a bounded, tenant-namespaced in-memory store for 15 minutes; task text and inputs are not returned or written to disk.

```json
{
  "task": "Research and compare three competitors, then draft a summary",
  "mode": "dive",
  "skill": "comparison"
}
```

The response contains `plan_id`, a sanitized `plan` summary, `created_at`, `expires_at`, and `reusable: true`. The summary describes intent, mode, skill, step types, and routed tools without returning task parameters, credentials, cookies, or raw page content.

## `POST /execute`

Executes a previously produced and inspected plan for the same organization. Execution reuses the stored plan object rather than generating a new plan, so approval and execution remain correlated. The route requires `solve:execute` and supports `Idempotency-Key` or `idempotency_key`.

```json
{ "plan_id": "plan_abc123", "output_format": "comparison" }
```

An unknown, expired, or cross-organization plan returns the same nondisclosing invalid-plan error. Browser actions still apply the existing isolation, origin, credential-reference, and session-state checks at execution time. A successful response is the regular grounded solve response plus the approved `plan_id`.

## `POST /observe` (agent variant)

Same underlying mechanism as [`/observe`](monitor.md), usable by agents to set up recurring watches as part of a larger workflow.

## `GET /diff`

Computes change since the last known state for a target — a thin wrapper over [`/memory/{target}/diff`](memory.md).

## `GET /report/{execution_id}`
Retrieves the full [execution graph](../../concepts/execution-graphs.md) for a run.

## `GET /report/{execution_id}/replay`

Returns a read-only historical projection of the persisted redacted trace. The projection contains ordered nodes, edges, timing, sanitized input/output summaries, and explicit `network_reexecuted: false` and `side_effects: false` flags. It never re-fetches a URL, opens a browser, sends a webhook, mutates memory, or performs another side effect. The route uses the same organization-scoped `memory:read` authorization and nondisclosing lookup behavior as the normal report route.


See [concepts/agents.md](../../concepts/agents.md) for the design rationale.
