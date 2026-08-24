"""Command-line entry point for the AgentWeb local server and migrations."""

from __future__ import annotations

import argparse
import json
import sys

from .api import create_server
from .engine import AgentWebEngine
from .maintenance import purge_retention
from .memory import MemoryStore
from .rdbms import DatabaseConfig, open_distributed_queue
from .secrets import build_provider


def _migration_main(argv: list[str]) -> None:
    from .migrations import export_sqlite_relational, import_postgres_relational
    from .rdbms import DatabaseConfig, PostgresRelationalStore

    parser = argparse.ArgumentParser(prog=f"agentweb {argv[0]}")
    if argv[0] == "migrate-export":
        parser.add_argument("--source", required=True, help="SQLite source database path.")
        parser.add_argument("--output", required=True, help="Directory for the migration manifest.")
        parser.add_argument("--dry-run", action="store_true", help="Validate and report without writing export files.")
        args = parser.parse_args(argv[1:])
        print(json.dumps(export_sqlite_relational(args.source, args.output, args.dry_run), indent=2, default=str))
        return
    parser.add_argument("--input", required=True, help="Migration manifest directory.")
    parser.add_argument("--dry-run", action="store_true", help="Validate the manifest without modifying PostgreSQL.")
    args = parser.parse_args(argv[1:])
    config = DatabaseConfig.from_environment()
    if config.driver != "postgres":
        raise SystemExit("migrate-import requires a PostgreSQL DATABASE_URL")
    store = PostgresRelationalStore(config.url, config.pool_size)
    try:
        print(json.dumps(import_postgres_relational(args.input, store, args.dry_run), indent=2, default=str))
    finally:
        store.close()


def _gc_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="agentweb gc")
    parser.add_argument("--data", default="agentweb.sqlite3", help="SQLite database path.")
    parser.add_argument("--snapshot-days", type=int, default=90, help="Snapshot retention window.")
    parser.add_argument("--trace-days", type=int, default=30, help="Trace retention window.")
    parser.add_argument("--metric-days", type=int, default=30, help="Metric retention window.")
    parser.add_argument("--org", default=None, help="Limit cleanup to one organization.")
    args = parser.parse_args(argv[1:])
    memory = MemoryStore(args.data)
    engine = AgentWebEngine(memory)
    print(json.dumps(purge_retention(memory, engine.traces, snapshot_retention_days=args.snapshot_days, trace_retention_days=args.trace_days, metric_retention_days=args.metric_days, org_id=args.org, metrics=engine.metrics), indent=2))


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in {"migrate-export", "migrate-import"}:
        _migration_main(sys.argv[1:])
        return
    if len(sys.argv) > 1 and sys.argv[1] == "gc":
        _gc_main(sys.argv[1:])
        return
    parser = argparse.ArgumentParser(description="Run the AgentWeb local API server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000).")
    parser.add_argument("--data", default="agentweb.sqlite3", help="SQLite database path (default: agentweb.sqlite3).")
    parser.add_argument("--worker", action="store_true", help="Run the durable monitor scheduler instead of the HTTP server.")
    parser.add_argument("--once", action="store_true", help="With --worker, execute one due job and exit.")
    parser.add_argument("--poll", type=float, default=1.0, help="With --worker, seconds between due-job polls (default: 1).")
    args = parser.parse_args()
    if args.worker:
        provider = build_provider()
        coordinator = open_distributed_queue(DatabaseConfig.from_environment(provider))
        engine = AgentWebEngine(MemoryStore(args.data), secret_provider=provider, queue_coordinator=coordinator)
        engine.scheduler.poll_seconds = max(0.1, args.poll)
        if args.once:
            print(json.dumps(engine.scheduler.run_once()))
            return
        print(f"AgentWeb scheduler running with {args.data}")
        try:
            engine.scheduler.run_forever()
        except KeyboardInterrupt:
            print("\nStopping AgentWeb scheduler.")
        return
    server = create_server(args.host, args.port, args.data)
    print(f"AgentWeb listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping AgentWeb.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
