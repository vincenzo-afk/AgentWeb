# Endpoints Overview

Base URL: `https://api.agentweb.dev/v1`

| Method | Path | Description |
|---|---|---|
| POST | `/plan` | Create a tenant-scoped expiring plan without executing it |
| POST | `/execute` | Execute a previously inspected plan; supports idempotency |
| POST | `/solve` | Run a one-shot grounded research task |
| GET | `/observe` | List organization monitors with cursor pagination |
| POST | `/observe` | Create a recurring monitor; supports idempotency |
| GET | `/observe/{id}` | Get monitor status/history |
| DELETE | `/observe/{id}` | Cancel a monitor; supports idempotency |
| POST | `/search` | Low-level search |
| POST | `/crawl` | Low-level bounded crawl; supports idempotency |
| GET | `/crawl` | List tenant-scoped crawl runs with cursor pagination |
| GET | `/crawl/{crawl_id}` | Retrieve one crawl run and its page metadata |
| POST | `/browser/sessions` | Open a browser session; may use opaque encrypted credential and origin-bound session-state references |
| POST | `/extract` | Structured extraction from a page or document |
| GET | `/memory/{target}` | Retrieve stored snapshots for a target |
| GET | `/memory/{target}/diff` | Compute diff between snapshots |
| GET | `/graph/query` | Query tenant-scoped graph nodes and edges with bounded depth and cursor pagination |
| POST | `/graph/entities` | Create or merge a graph entity |
| POST | `/graph/relations` | Create or corroborate a graph relation |
| GET | `/workflows` | List tenant-scoped workflow definitions |
| POST | `/workflows` | Register a monitor-event workflow; supports idempotency |
| POST | `/workflows/pause` | Pause a workflow definition |
| POST | `/workflows/resume` | Resume a workflow definition |
| GET | `/workflows/runs` | List tenant-scoped workflow runs |
| GET | `/learning/summary` | Read aggregate strategy and mode outcomes |
| POST | `/learning/outcomes` | Record bounded evaluator feedback without raw task content |
| GET | `/report/{execution_id}` | Retrieve an execution graph |
| GET | `/admin/keys` | List redacted API keys with cursor pagination |
| POST | `/admin/keys` | Create an API key with idempotency support |
| DELETE | `/admin/keys/{id}` | Revoke an API key with idempotency support |
| GET | `/admin/browser-credentials` | List non-secret browser credential metadata |
| POST | `/admin/browser-credentials` | Create an encrypted browser credential; supports idempotency |
| DELETE | `/admin/browser-credentials/{id}` | Revoke an encrypted browser credential with idempotency support |
| GET | `/admin/browser-session-states` | List non-secret encrypted browser session-state metadata |
| POST | `/admin/browser-session-states` | Create encrypted origin-bound browser storage state; supports idempotency |
| DELETE | `/admin/browser-session-states/{id}` | Revoke encrypted browser session state with idempotency support |
| GET | `/admin/audit` | List immutable security events with cursor pagination and optional action/actor/target/time-range filters |
| GET | `/admin/usage` | View organization usage and estimated billing |
| DELETE | `/admin/data` | Delete selected organization-owned snapshots, crawl history, browser session states, graph/vector data, learning outcomes, workflows, or execution traces; supports idempotency |
| GET | `/admin/metrics` | Read organization-scoped operational metrics |

List endpoints use the opaque `cursor` and bounded `limit` query parameters described in [pagination.md](pagination.md). Full request and response schemas are in [reference/](reference/search.md).

All implemented higher-level capabilities remain bounded and tenant-scoped. Graph queries, plan/execute workflows, learning summaries, and queued event-driven runs do not imply autonomous policy changes or external managed services.
