# Endpoints Overview

Base URL: `https://api.agentweb.dev/v1`

| Method | Path | Description |
|---|---|---|
| POST | `/solve` | Run a one-shot grounded research task |
| POST | `/observe` | Create a recurring monitor |
| GET | `/observe/{id}` | Get monitor status/history |
| DELETE | `/observe/{id}` | Cancel a monitor |
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
| GET | `/admin/keys` | Manage API keys |
| GET | `/admin/usage` | View usage and billing |

Full request/response schemas are in [reference/](reference/search.md).
