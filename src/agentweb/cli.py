"""Command-line entry point for the AgentWeb local server."""

from __future__ import annotations

import argparse
import json

from .api import create_server
from .engine import AgentWebEngine
from .memory import MemoryStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AgentWeb local API server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000).")
    parser.add_argument(
        "--data",
        default="agentweb.sqlite3",
        help="SQLite database path (default: agentweb.sqlite3).",
    )
    parser.add_argument(
        "--worker",
        action="store_true",
        help="Run the durable monitor scheduler instead of the HTTP server.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="With --worker, execute one due job and exit.",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=1.0,
        help="With --worker, seconds between due-job polls (default: 1).",
    )
    args = parser.parse_args()
    if args.worker:
        engine = AgentWebEngine(MemoryStore(args.data))
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
