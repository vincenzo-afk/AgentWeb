# Environment Variables

| Variable | Required | Description |
|---|---|---|
| `AGENTWEB_ENV` | Yes | `production` \| `staging` \| `development` |
| `DATABASE_URL` | Yes | Relational store connection string |
| `SNAPSHOT_STORE_URL` | Yes | Blob store connection string |
| `GRAPH_STORE_URL` | Yes | Graph database connection string |
| `AGENTWEB_DISTRIBUTED_QUEUE` | No | Set to `1`/`true`/`yes` to coordinate scheduler leases and rate limits through PostgreSQL; requires a PostgreSQL `DATABASE_URL` |
| `WEBHOOK_SIGNING_KEY` | Yes | Platform-side key used to derive per-org webhook signing secrets |
| `AGENTWEB_SEARCH_PROVIDER` | No | `duckduckgo` by default; use `json` for an HTTP JSON provider |
| `AGENTWEB_SEARCH_ENDPOINT` | Conditional | HTTP(S) endpoint required for the `json` provider |
| `AGENTWEB_SEARCH_API_KEY` | No | Provider credential resolved through the external secret boundary when configured |
| `AGENTWEB_SEARCH_TIMEOUT_SECONDS` | No | Provider timeout, bounded by the implementation |
| `AGENTWEB_BROWSER_WORKERS` | No | Maximum concurrent browser sessions in one process; bounded to 1–16 and defaults to 2 |
| `AGENTWEB_CRAWL_MIN_INTERVAL_SECONDS` | No | Minimum delay between requests to the same crawler host; defaults to 0.1 seconds |
| `LOG_LEVEL` | No | Defaults to `info`; see [../observability/LOGGING.md](../observability/LOGGING.md) |

When `AGENTWEB_DISTRIBUTED_QUEUE` is enabled, every API/worker instance must use the same PostgreSQL `DATABASE_URL`; PostgreSQL performs atomic `SKIP LOCKED` job claims and stores organization-scoped token buckets. Local SQLite remains the default when the switch is absent. Stale workers cannot acknowledge or fail a reclaimed job because every lease carries an ownership token.

Secrets (`DATABASE_URL`, `WEBHOOK_SIGNING_KEY`, etc.) must be sourced from a secrets manager in staging/production, never committed — see [../../docs/security/secrets-management.md](../../docs/security/secrets-management.md).
