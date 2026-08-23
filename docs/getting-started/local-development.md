# Local Development

The repository contains a dependency-free Python implementation of the AgentWeb Phase 0/1 building blocks. It uses Python 3.11 or newer and SQLite for local monitor, snapshot, and trace state.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable .
```

## Run the server

```bash
agentweb --host 127.0.0.1 --port 8000 --data agentweb.sqlite3
```

The liveness endpoint is available at `http://127.0.0.1:8000/health`. The API accepts bearer authentication when `AGENTWEB_API_KEY` or `AGENTWEB_API_KEYS` is configured; otherwise it runs in local development mode.

## Verify changes

```bash
python3 -m compileall -q src tests scripts
PYTHONPATH=src python3 scripts/validate_project.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Tests use local HTTP fixtures and do not require a live search provider. The `AGENTWEB_ALLOW_PRIVATE_TARGETS=1` setting is used only by local fixture tests; it must not be enabled for a network-facing deployment.

## Current implementation boundary

Implemented modules include the HTTP API, search adapter, bounded same-origin crawler, parser, normalizer, extractor, basic ranking, trust and safety gate, SQLite memory, request-driven monitor checks, signed webhook delivery, bearer scope checks, rate limiting, and SQLite execution traces. The scheduler, rendered browser worker, knowledge graph, agent-native plan/execute APIs, and background event workflows remain roadmap work.
