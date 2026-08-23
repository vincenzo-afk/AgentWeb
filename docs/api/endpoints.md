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
| POST | `/browser/sessions` | Open a browser session |
| POST | `/extract` | Structured extraction from a page or document |
| GET | `/memory/{target}` | Retrieve stored snapshots for a target |
| GET | `/memory/{target}/diff` | Compute diff between snapshots |
| GET | `/graph/query` | Query the knowledge graph |
| POST | `/plan` | Produce a plan without executing |
| POST | `/execute` | Execute a previously produced plan |
| GET | `/report/{execution_id}` | Retrieve an execution graph |
| GET | `/admin/keys` | List redacted API keys with cursor pagination |
| POST | `/admin/keys` | Create an API key with idempotency support |
| DELETE | `/admin/keys/{id}` | Revoke an API key with idempotency support |
| GET | `/admin/audit` | List immutable security events with cursor pagination |
| GET | `/admin/usage` | View organization usage and estimated billing |

List endpoints use the opaque `cursor` and bounded `limit` query parameters described in [pagination.md](pagination.md). Full request/response schemas are in [reference/](reference/search.md). Graph, plan, and execute routes remain roadmap work and are not exposed by the current OpenAPI contract.
