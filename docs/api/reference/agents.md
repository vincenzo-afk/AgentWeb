# Agent APIs

Endpoints designed for autonomous agents that need to plan, execute, observe, and audit multi-step internet work independently (see [roadmap.md](../../roadmap.md) Phase 3).

## `POST /plan`

Produces a plan without executing it, for inspection or approval before running.

```json
{ "task": "Research and compare three competitors, then draft a summary" }
```

Returns a `plan` object describing intended steps.

## `POST /execute`

Executes a previously produced plan.

```json
{ "plan_id": "plan_abc123" }
```

## `POST /observe` (agent variant)

Same underlying mechanism as [`/observe`](monitor.md), usable by agents to set up recurring watches as part of a larger workflow.

## `GET /diff`

Computes change since the last known state for a target — a thin wrapper over [`/memory/{target}/diff`](memory.md).

## `GET /report/{execution_id}`
Retrieves the full [execution graph](../../concepts/execution-graphs.md) for a run.

## `GET /report/{execution_id}/replay`

Returns a read-only historical projection of the persisted redacted trace. The projection contains ordered nodes, edges, timing, sanitized input/output summaries, and explicit `network_reexecuted: false` and `side_effects: false` flags. It never re-fetches a URL, opens a browser, sends a webhook, mutates memory, or performs another side effect. The route uses the same organization-scoped `memory:read` authorization and nondisclosing lookup behavior as the normal report route.


See [concepts/agents.md](../../concepts/agents.md) for the design rationale.
