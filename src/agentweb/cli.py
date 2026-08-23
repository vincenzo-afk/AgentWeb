"""Command-line entry point for the AgentWeb local server."""

from __future__ import annotations

import argparse

from .api import create_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AgentWeb local API server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000).")
    parser.add_argument(
        "--data",
        default="agentweb.sqlite3",
        help="SQLite database path (default: agentweb.sqlite3).",
    )
    args = parser.parse_args()
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
