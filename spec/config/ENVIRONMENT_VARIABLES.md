# Environment Variables

| Variable | Required | Description |
|---|---|---|
| `AGENTWEB_ENV` | Yes | `production` \| `staging` \| `development` |
| `DATABASE_URL` | Yes | Relational store connection string |
| `SNAPSHOT_STORE_URL` | Yes | Blob store connection string |
| `GRAPH_STORE_URL` | Yes | Graph database connection string |
| `QUEUE_URL` | Yes | Job queue broker connection string |
| `WEBHOOK_SIGNING_KEY` | Yes | Platform-side key used to derive per-org webhook signing secrets |
| `AGENTWEB_SEARCH_PROVIDER` | No | `duckduckgo` by default; use `json` for an HTTP JSON provider |
| `AGENTWEB_SEARCH_ENDPOINT` | Conditional | HTTP(S) endpoint required for the `json` provider |
| `AGENTWEB_SEARCH_API_KEY` | No | Provider credential resolved through the external secret boundary when configured |
| `AGENTWEB_SEARCH_TIMEOUT_SECONDS` | No | Provider timeout, bounded by the implementation |
| `BROWSER_WORKER_POOL_SIZE` | No | Defaults per [DEFAULTS.md](DEFAULTS.md) |
| `LOG_LEVEL` | No | Defaults to `info`; see [../observability/LOGGING.md](../observability/LOGGING.md) |

Secrets (`DATABASE_URL`, `WEBHOOK_SIGNING_KEY`, etc.) must be sourced from a secrets manager in staging/production, never committed — see [../../docs/security/secrets-management.md](../../docs/security/secrets-management.md).
