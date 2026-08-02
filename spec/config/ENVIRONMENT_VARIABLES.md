# Environment Variables

| Variable | Required | Description |
|---|---|---|
| `AGENTWEB_ENV` | Yes | `production` \| `staging` \| `development` |
| `DATABASE_URL` | Yes | Relational store connection string |
| `SNAPSHOT_STORE_URL` | Yes | Blob store connection string |
| `GRAPH_STORE_URL` | Yes | Graph database connection string |
| `QUEUE_URL` | Yes | Job queue broker connection string |
| `WEBHOOK_SIGNING_KEY` | Yes | Platform-side key used to derive per-org webhook signing secrets |
| `BROWSER_WORKER_POOL_SIZE` | No | Defaults per [DEFAULTS.md](DEFAULTS.md) |
| `LOG_LEVEL` | No | Defaults to `info`; see [../observability/LOGGING.md](../observability/LOGGING.md) |

Secrets (`DATABASE_URL`, `WEBHOOK_SIGNING_KEY`, etc.) must be sourced from a secrets manager in staging/production, never committed — see [../../docs/security/secrets-management.md](../../docs/security/secrets-management.md).
