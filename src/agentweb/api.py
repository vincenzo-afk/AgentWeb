"""Dependency-free HTTP API for AgentWeb's Phase 0/1 MVP."""

from __future__ import annotations

import json
import os
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .auth import Authenticator, RateLimiter
from .engine import AgentWebEngine
from .errors import AgentWebError, InvalidRequestError, NotFoundError
from .search import search


class AgentWebHandler(BaseHTTPRequestHandler):
    server_version = "AgentWeb/0.2"

    @property
    def engine(self) -> AgentWebEngine:
        return self.server.engine  # type: ignore[attr-defined]

    @property
    def authenticator(self) -> Authenticator:
        return self.server.authenticator  # type: ignore[attr-defined]

    @property
    def rate_limiter(self) -> RateLimiter:
        return self.server.rate_limiter  # type: ignore[attr-defined]

    def _send_json(self, status: int, payload: dict | list | None = None, request_id: str | None = None) -> None:
        body = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        if request_id:
            self.send_header("X-Request-ID", request_id)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _error(self, error: AgentWebError, request_id: str) -> None:
        error.request_id = request_id
        self._send_json(error.status_code, error.as_dict(), request_id)

    def _authenticate(self, scope: str, request_id: str):
        try:
            principal = self.authenticator.authenticate(self.headers.get("Authorization"), scope)
            self.rate_limiter.check(principal.key_id, 2.0 if scope == "solve:execute" else 1.0)
            return principal
        except AgentWebError as error:
            self._error(error, request_id)
            return None

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise InvalidRequestError("Content-Length must be an integer") from error
        if length > 1_000_000:
            raise InvalidRequestError("request body is too large")
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InvalidRequestError("request body must be valid JSON") from error
        if not isinstance(payload, dict):
            raise InvalidRequestError("request body must be a JSON object")
        return payload

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json(HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:  # noqa: N802
        request_id = "req_" + uuid.uuid4().hex[:16]
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok", "service": "agentweb"}, request_id)
            return
        if self._authenticate("memory:read" if path.startswith(("/memory/", "/report/")) else "observe:manage", request_id) is None:
            return
        try:
            if path.startswith("/observe/"):
                monitor_id = path.rsplit("/", 1)[-1]
                monitor = self.engine.memory.get_monitor(monitor_id)
                if not monitor:
                    raise NotFoundError("monitor not found")
                self._send_json(HTTPStatus.OK, self.engine.check_monitor(monitor).to_dict(), request_id)
                return
            if path.startswith("/report/"):
                execution_id = path.rsplit("/", 1)[-1]
                trace = self.engine.traces.get(execution_id)
                if not trace:
                    raise NotFoundError("execution trace not found")
                self._send_json(HTTPStatus.OK, trace, request_id)
                return
            if path.startswith("/memory/"):
                target_part = path[len("/memory/") :]
                if target_part.endswith("/diff"):
                    target = unquote(target_part[: -len("/diff")].rstrip("/"))
                    query = parse_qs(urlparse(self.path).query)
                    from_hash = query.get("from", [""])[0]
                    to_hash = query.get("to", [""])[0]
                    if not from_hash or not to_hash:
                        raise InvalidRequestError("memory diff requires from and to query parameters")
                    try:
                        payload = self.engine.memory.diff(target, from_hash, to_hash)
                    except KeyError as error:
                        raise NotFoundError(str(error)) from error
                    self._send_json(HTTPStatus.OK, payload, request_id)
                    return
                target = unquote(target_part)
                snapshots = self.engine.memory.list_snapshots(target)
                self._send_json(HTTPStatus.OK, {"target": target, "snapshots": snapshots}, request_id)
                return
            raise NotFoundError("route not found")
        except AgentWebError as error:
            self._error(error, request_id)

    def do_DELETE(self) -> None:  # noqa: N802
        request_id = "req_" + uuid.uuid4().hex[:16]
        if self._authenticate("observe:manage", request_id) is None:
            return
        path = urlparse(self.path).path
        try:
            if path.startswith("/observe/"):
                monitor_id = path.rsplit("/", 1)[-1]
                if not self.engine.memory.delete_monitor(monitor_id):
                    raise NotFoundError("monitor not found")
                self._send_json(HTTPStatus.NO_CONTENT, request_id=request_id)
                return
            raise NotFoundError("route not found")
        except AgentWebError as error:
            self._error(error, request_id)

    def do_POST(self) -> None:  # noqa: N802
        request_id = "req_" + uuid.uuid4().hex[:16]
        path = urlparse(self.path).path
        scope = {
            "/solve": "solve:execute",
            "/observe": "observe:manage",
            "/search": "search:read",
            "/extract": "extract:read",
            "/crawl": "search:read",
        }.get(path)
        if scope is None:
            self._error(NotFoundError("route not found"), request_id)
            return
        if self._authenticate(scope, request_id) is None:
            return
        try:
            payload = self._read_json()
            if path == "/solve":
                response = self.engine.solve(payload.get("task", ""), payload.get("mode", "focus"))
                self._send_json(HTTPStatus.OK, response.to_dict(), request_id)
            elif path == "/observe":
                monitor = self.engine.create_monitor(
                    payload.get("task", ""), payload.get("frequency", "daily"), payload.get("webhook_url")
                )
                self._send_json(HTTPStatus.OK, monitor.to_dict(), request_id)
            elif path == "/search":
                query = payload.get("query", "")
                self._send_json(HTTPStatus.OK, {"query": query, "results": search(query, payload.get("limit", 10))}, request_id)
            elif path == "/extract":
                self._send_json(
                    HTTPStatus.OK,
                    self.engine.extract(payload.get("url", ""), payload.get("schema")),
                    request_id,
                )
            elif path == "/crawl":
                result = self.engine.crawler.crawl(
                    payload.get("start_url", ""),
                    payload.get("max_pages", 50),
                    payload.get("depth", 2),
                    payload.get("url_pattern"),
                )
                self._send_json(HTTPStatus.OK, result.to_dict(), request_id)
        except AgentWebError as error:
            self._error(error, request_id)
        except (ValueError, TypeError) as error:
            self._error(InvalidRequestError(str(error)), request_id)
        except RuntimeError as error:
            from .errors import UpstreamError

            self._error(UpstreamError(str(error)), request_id)
        except Exception as error:  # defensive API boundary; details stay local
            from .errors import AgentWebError as InternalError

            self._error(InternalError(str(error)), request_id)

    def log_message(self, format: str, *args: object) -> None:
        if os.getenv("AGENTWEB_QUIET") != "1":
            super().log_message(format, *args)


def create_server(host: str = "127.0.0.1", port: int = 8000, data_path: str = "agentweb.sqlite3"):
    from .memory import MemoryStore

    server = ThreadingHTTPServer((host, port), AgentWebHandler)
    store = MemoryStore(data_path)
    server.engine = AgentWebEngine(store)  # type: ignore[attr-defined]
    server.authenticator = Authenticator()  # type: ignore[attr-defined]
    server.rate_limiter = RateLimiter()  # type: ignore[attr-defined]
    return server
