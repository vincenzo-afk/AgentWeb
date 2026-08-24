# Endpoints Overview

Base URL: `https://api.agentweb.dev/v1`

| Method | Path | Description |
|---|---|---|
| POST | `/solve` | Run a one-shot grounded research task |
| GET | `/observe` | List organization monitors with cursor pagination |
| POST | `/observe` | Create a recurring monitor; supports idempotency |
| GET | `/observe/{id}` | Get monitor status/history |
| DELETE | `/observe/{id}` | Cancel a monitor; supports idempotency |
| POST | `/search` | Low-level search |
| POST | `/crawl` | Low-level crawl |
| POST | `/browser/sessions` | Open a browser session; may use an opaque encrypted-credential reference |
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
| GET | `/admin/audit` | List immutable security events with cursor pagination and optional action/actor/target/time-range filters |
| GET | `/admin/usage` | View organization usage and estimated billing |
| DELETE | `/admin/data` | Delete organization-owned snapshots and execution traces; supports idempotency |
| GET | `/admin/metrics` | Read organization-scoped operational metrics |

List endpoints use the opaque `cursor` and bounded `limit` query parameters described in [pagination.md](pagination.md). Full request/response schemas are in [reference/](reference/search.md).

The following roadmap capabilities are intentionally not exposed by the current API: `GET /graph/query`, `POST /plan`, and `POST /execute`. They remain gated by the Phase 2 and Phase 3 roadmap decisions.
