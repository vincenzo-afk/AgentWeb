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
| DELETE | `/admin/data` | Delete organization-owned snapshots, crawl history, browser session states, or execution traces; supports idempotency |
| GET | `/admin/metrics` | Read organization-scoped operational metrics |

List endpoints use the opaque `cursor` and bounded `limit` query parameters described in [pagination.md](pagination.md). Full request/response schemas are in [reference/](reference/search.md).

The following roadmap capability remains intentionally unexposed by the current API: `GET /graph/query`. Graph query execution remains gated by the Phase 2 roadmap decision. The plan/execute pair is now available as a bounded local-first agent workflow; it does not introduce graph reasoning, intervention, or learning-loop persistence.
