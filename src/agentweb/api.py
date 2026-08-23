"""Dependency-free HTTP API for AgentWeb's Phase 0 MVP."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .engine import AgentWebEngine
from .search import search


class AgentWebHandler(BaseHTTPRequestHandler):
    server_version = "AgentWeb/0.1"

    @property
    def engine(self) -> AgentWebEngine:
        return self.server.engine  # type: ignore[attr-defined]

    def _send_json(self, status: int, payload: dict | list | None = None) -> None:
        body = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _error(self, status: int, message: str, error_type: str = "invalid_request") -> None:
        self._send_json(status, {"error": {"type": error_type, "message": message}})

    def _authorized(self) -> bool:
        expected = os.getenv("AGENTWEB_API_KEY")
        if not expected:
            return True
        authorization = self.headers.get("Authorization", "")
        return authorization == f"Bearer {expected}"

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("request body is too large")
        raw = self.rfile.read(length)
        if not raw:
            return {}
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json(HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            self._error(HTTPStatus.UNAUTHORIZED, "missing or invalid API key", "unauthorized")
            return
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok", "service": "agentweb"})
            return
        if path.startswith("/observe/"):
            monitor_id = path.rsplit("/", 1)[-1]
            monitor = self.engine.memory.get_monitor(monitor_id)
            if not monitor:
                self._error(HTTPStatus.NOT_FOUND, "monitor not found", "not_found")
                return
            self._send_json(HTTPStatus.OK, self.engine.check_monitor(monitor).to_dict())
            return
        self._error(HTTPStatus.NOT_FOUND, "route not found", "not_found")

    def do_DELETE(self) -> None:  # noqa: N802
        if not self._authorized():
            self._error(HTTPStatus.UNAUTHORIZED, "missing or invalid API key", "unauthorized")
            return
        path = urlparse(self.path).path
        if path.startswith("/observe/"):
            monitor_id = path.rsplit("/", 1)[-1]
            if not self.engine.memory.delete_monitor(monitor_id):
                self._error(HTTPStatus.NOT_FOUND, "monitor not found", "not_found")
                return
            self._send_json(HTTPStatus.NO_CONTENT)
            return
        self._error(HTTPStatus.NOT_FOUND, "route not found", "not_found")

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            self._error(HTTPStatus.UNAUTHORIZED, "missing or invalid API key", "unauthorized")
            return
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/solve":
                response = self.engine.solve(payload.get("task", ""), payload.get("mode", "focus"))
                self._send_json(HTTPStatus.OK, response.to_dict())
            elif path == "/observe":
                monitor = self.engine.create_monitor(payload.get("task", ""), payload.get("frequency", "daily"))
                self._send_json(HTTPStatus.OK, monitor.to_dict())
            elif path == "/search":
                query = payload.get("query", "")
                limit = payload.get("limit", 10)
                self._send_json(HTTPStatus.OK, {"query": query, "results": search(query, limit=limit)})
            elif path == "/extract":
                self._send_json(
                    HTTPStatus.OK,
                    self.engine.extract(payload.get("url", ""), payload.get("schema")),
                )
            else:
                self._error(HTTPStatus.NOT_FOUND, "route not found", "not_found")
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))
        except RuntimeError as error:
            self._error(HTTPStatus.BAD_GATEWAY, str(error), "upstream_error")
        except Exception as error:  # defensive API boundary; details stay local
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, str(error), "internal_error")

    def log_message(self, format: str, *args: object) -> None:
        if os.getenv("AGENTWEB_QUIET") != "1":
            super().log_message(format, *args)


def create_server(host: str = "127.0.0.1", port: int = 8000, data_path: str = "agentweb.sqlite3"):
    server = ThreadingHTTPServer((host, port), AgentWebHandler)
    server.engine = AgentWebEngine()  # type: ignore[attr-defined]
    if data_path != "agentweb.sqlite3":
        from .memory import MemoryStore

        server.engine = AgentWebEngine(MemoryStore(data_path))  # type: ignore[attr-defined]
    return server
