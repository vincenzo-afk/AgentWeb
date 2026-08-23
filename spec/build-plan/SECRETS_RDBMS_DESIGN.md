# External Secrets and Production RDBMS Design

This build slice adds production provider boundaries while retaining the current SQLite deployment for local development and deterministic tests.

## Secret provider boundary

`SecretProvider` resolves named platform secrets such as `DATABASE_URL`, `WEBHOOK_SIGNING_KEY`, and `AGENTWEB_API_KEYS`. The default provider reads environment variables only in `development`. In `staging` and `production`, configuration fails closed unless a provider is explicitly configured. The first free implementation supports an injected in-process mapping for tests and a command-backed provider whose executable receives only the secret name and returns the value on stdout; command output is never logged. A provider cache stores values only in process memory with a short TTL and never serializes them.

Customer API keys remain separate: they are PBKDF2-derived hashes in the relational store and are not passed through the platform secret provider. Browser credentials remain out of scope for this slice and continue to be rejected by the browser action contract.

## Relational adapter boundary

`RelationalStore` exposes the organization, API-key, monitor, scheduler-job, run, usage, and audit records required by the relational schema. SQLite remains the default local implementation. A DB-API-compatible PostgreSQL adapter is optional and activated by `DATABASE_URL=postgresql://...` plus the `postgres` extra; it uses parameterized SQL, a bounded connection pool, explicit transaction contexts, and the same organization ownership predicates.

The adapter is intentionally narrow rather than pretending all SQLite SQL is portable. A schema bootstrap/migration module contains versioned, idempotent DDL for `organizations`, `api_keys`, `runs`, `monitors`, `scheduler_jobs`, `audit_events`, and `usage_records` plus required tenant indexes. The migration command supports `--dry-run`, refuses to run against an unknown environment, validates required legacy fields, converts epoch timestamps to timezone-aware values, adapts JSON strings to PostgreSQL JSONB, and records applied versions in `schema_migrations`.

## Migration and rollback

The migration is additive and backward-compatible. Existing SQLite databases are exported to a JSON-lines transfer manifest with content hashes and row counts; no source database is mutated. A production import runs in a transaction, validates counts and hashes, then marks the migration version. Rollback means stopping the new API tier and continuing on the old SQLite path until the RDBMS import is corrected; destructive down-migrations are deliberately not provided.

## Runtime configuration

`AGENTWEB_ENV` defaults to `development` only when absent. `DATABASE_URL` is required outside development. `AGENTWEB_SECRET_PROVIDER` accepts `env`, `mapping`, or `command`; production rejects `env`. `AGENTWEB_SECRET_COMMAND` is required for the command provider. `AGENTWEB_SECRET_TTL_SECONDS` is bounded to a short in-process cache. Secret names and metadata may appear in diagnostics, but secret values never appear in logs, traces, manifests, or error messages.

## Explicit constraints

This slice does not claim a managed cloud secret backend, distributed connection pooling, zero-downtime dual writes, snapshot/blob migration, graph migration, or automated production deployment. It supplies the provider and relational contracts needed for those integrations without silently weakening local compatibility or rollback safety.
