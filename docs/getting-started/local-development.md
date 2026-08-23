# Local Development

The repository contains a dependency-free Python implementation of the AgentWeb Phase 0/1 building blocks. It uses Python 3.11 or newer and SQLite for local monitor, snapshot, and trace state.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable .
# Optional rendered-browser support:
python -m pip install --editable '.[browser]'
# Optional production PostgreSQL adapter and migration tooling:
python -m pip install --editable '.[production]'
```

## Run the server

```bash
agentweb --host 127.0.0.1 --port 8000 --data agentweb.sqlite3
```

The liveness endpoint is available at `http://127.0.0.1:8000/health`. The API accepts bearer authentication when `AGENTWEB_API_KEY` or `AGENTWEB_API_KEYS` is configured; otherwise it runs in local development mode. In staging and production, set `AGENTWEB_ENV` and use an external secret provider; the application rejects the environment provider outside development.

For rendered sessions, set `AGENTWEB_CHROMIUM_PATH` to an installed Chromium-compatible binary. The browser adapter creates a new context per request and supports `click`, `type`, `wait_for`, `scroll`, and `extract` actions.

The default search path is the free DuckDuckGo HTML adapter. To use a licensed or self-hosted HTTP JSON provider, set `AGENTWEB_SEARCH_PROVIDER=json` and `AGENTWEB_SEARCH_ENDPOINT=https://search.example.test/query`. The endpoint receives `q`, `limit`, and optional `freshness` query parameters and returns either a result array or `{ "results": [...] }`. If `AGENTWEB_SEARCH_API_KEY` is needed, resolve it through the configured external secret provider rather than committing it to the environment template or repository. A failed configured provider falls back to DuckDuckGo and returns an empty list only if both providers are unavailable.

Run the production scheduler as a separately supervised process so HTTP restarts cannot interrupt monitor timing:

```bash
export AGENTWEB_CHROMIUM_PATH=/usr/bin/chromium
agentweb --worker --data agentweb.sqlite3
```

Use `agentweb --worker --once --data agentweb.sqlite3` for a single due-job execution. The queue persists monitor jobs in SQLite, claims them with a lease, prioritizes minutely monitors, retries failures, and moves exhausted jobs to `dead_letter`.

For a Linux deployment, [`deploy/agentweb-scheduler.service`](../../deploy/agentweb-scheduler.service) provides a restart-on-failure systemd template. It runs the worker as a dedicated user, keeps the data directory writable only where needed, and enables `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem`, and `ProtectHome`.

## External secrets and PostgreSQL migration

The free local provider reads environment values only in development. For a production-shaped test, use an executable that accepts a validated secret name and prints only that secret value, then configure `AGENTWEB_SECRET_PROVIDER=command` and `AGENTWEB_SECRET_COMMAND=/path/to/provider`. The command provider applies a five-second timeout, never logs stdout, and caches values only in memory for a bounded TTL.

Export the relational portion of a local SQLite database without mutating the source:

```bash
agentweb migrate-export --source agentweb.sqlite3 --output ./migration-export
agentweb migrate-export --source agentweb.sqlite3 --output ./migration-export --dry-run
```

With `AGENTWEB_ENV=production`, a PostgreSQL `DATABASE_URL` resolved through the configured secret provider, and `.[production]` installed, validate or apply the manifest transactionally:

```bash
agentweb migrate-import --input ./migration-export --dry-run
agentweb migrate-import --input ./migration-export
```

The import is additive and idempotent. It verifies table checksums, bootstraps the required indexes, records `relational-v1`, and provides no destructive down-migration. If deployment smoke tests fail, stop the new API tier and continue on the prior SQLite-compatible release while correcting the migration.

## Verify changes

```bash
python3 -m compileall -q src tests scripts
PYTHONPATH=src python3 scripts/validate_project.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Tests use local HTTP fixtures and do not require a live search provider. The `AGENTWEB_ALLOW_PRIVATE_TARGETS=1` setting is used only by local fixture tests; it must not be enabled for a network-facing deployment.

## Current implementation boundary

Implemented modules include the HTTP API, provider-backed search with free fallback, bounded same-origin crawler, parser, confidence-bearing normalizer and extractor, basic ranking, trust and safety gate, isolated rendered browser sessions, SQLite memory, durable monitor jobs, request-driven and scheduled checks, signed webhook delivery, bearer scope checks, rate limiting, organization-scoped SQLite execution traces, fail-closed secret-provider modes, a bounded PostgreSQL relational adapter, and additive migration tooling. The knowledge graph, agent-native plan/execute APIs, distributed dual-write cutover, and event-driven workflows remain roadmap work.
