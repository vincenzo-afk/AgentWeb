# Local Development

The repository contains a dependency-free Python implementation of the AgentWeb Phase 0/1 building blocks. It uses Python 3.11 or newer and SQLite for local monitor, snapshot, and trace state.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable .
# Optional rendered-browser support:
python -m pip install --editable '.[browser]'
```

## Run the server

```bash
agentweb --host 127.0.0.1 --port 8000 --data agentweb.sqlite3
```

The liveness endpoint is available at `http://127.0.0.1:8000/health`. The API accepts bearer authentication when `AGENTWEB_API_KEY` or `AGENTWEB_API_KEYS` is configured; otherwise it runs in local development mode.

For rendered sessions, set `AGENTWEB_CHROMIUM_PATH` to an installed Chromium-compatible binary. The browser adapter creates a new context per request and supports `click`, `type`, `wait_for`, `scroll`, and `extract` actions.

Run the production scheduler as a separately supervised process so HTTP restarts cannot interrupt monitor timing:

```bash
export AGENTWEB_CHROMIUM_PATH=/usr/bin/chromium
agentweb --worker --data agentweb.sqlite3
```

Use `agentweb --worker --once --data agentweb.sqlite3` for a single due-job execution. The queue persists monitor jobs in SQLite, claims them with a lease, prioritizes minutely monitors, retries failures, and moves exhausted jobs to `dead_letter`.

For a Linux deployment, [`deploy/agentweb-scheduler.service`](../../deploy/agentweb-scheduler.service) provides a restart-on-failure systemd template. It runs the worker as a dedicated user, keeps the data directory writable only where needed, and enables `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem`, and `ProtectHome`.

## Verify changes

```bash
python3 -m compileall -q src tests scripts
PYTHONPATH=src python3 scripts/validate_project.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Tests use local HTTP fixtures and do not require a live search provider. The `AGENTWEB_ALLOW_PRIVATE_TARGETS=1` setting is used only by local fixture tests; it must not be enabled for a network-facing deployment.

## Current implementation boundary

Implemented modules include the HTTP API, search adapter, bounded same-origin crawler, parser, normalizer, extractor, basic ranking, trust and safety gate, isolated rendered browser sessions, SQLite memory, durable monitor jobs, request-driven and scheduled checks, signed webhook delivery, bearer scope checks, rate limiting, and SQLite execution traces. The knowledge graph, agent-native plan/execute APIs, and event-driven workflows remain roadmap work.
