"""Dependency-free HTTP API with tenant-scoped authorization and storage access."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import os
import re
import time
from datetime import datetime, timezone
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .auth import Authenticator, RateLimiter
from .engine import AgentWebEngine
from .errors import AgentWebError, ConflictError, InvalidRequestError, NotFoundError, PermissionError
from .redaction import redact_url
from .rdbms import DatabaseConfig, open_distributed_queue
from .search import search
from .secrets import build_provider


def _request_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _normalize_api_path(path: str) -> tuple[str, bool]:
    if path == "/v1":
        return "/", True
    if path.startswith("/v1/"):
        return path[3:], True
    return path, False


def _decode_cursor(value: str) -> int:
    if not value:
        return 0
    try:
        decoded = json.loads(base64.urlsafe_b64decode(value.encode("ascii") + b"===").decode("utf-8"))
        offset = int(decoded["offset"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError, binascii.Error):
        raise InvalidRequestError("cursor is invalid")
    if offset < 0:
        raise InvalidRequestError("cursor is invalid")
    return offset


def _encode_cursor(offset: int) -> str:
    raw = json.dumps({"offset": offset}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _parse_audit_timestamp(query: dict[str, list[str]], name: str) -> float | None:
    raw = query.get(name, [None])[0]
    if raw is None or raw == "":
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        try:
            value = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
        except (TypeError, ValueError):
            raise InvalidRequestError(f"{name} must be a Unix timestamp or ISO-8601 UTC time")
    if not math.isfinite(value):
        raise InvalidRequestError(f"{name} must be a finite timestamp")
    return value


def _audit_filter(query: dict[str, list[str]], name: str) -> str | None:
    raw = query.get(name, [None])[0]
    if raw is None:
        return None
    value = raw.strip()
    if not value or len(value) > 200:
        raise InvalidRequestError(f"{name} must contain between 1 and 200 characters")
    return value


def _query_value(query: dict[str, list[str]], name: str) -> str | None:
    raw = query.get(name, [None])[0]
    if raw is None:
        return None
    value = raw.strip()
    if not value or len(value) > 200:
        raise InvalidRequestError(f"{name} must contain between 1 and 200 characters")
    return value


def _page_window(query: dict[str, list[str]]) -> tuple[int, int]:
    try:
        limit = int(query.get("limit", ["50"])[0])
    except (ValueError, TypeError):
        raise InvalidRequestError("limit must be an integer")
    if limit < 1 or limit > 100:
        raise InvalidRequestError("limit must be between 1 and 100")
    return limit, _decode_cursor(query.get("cursor", [""])[0])


def _page(items: list, query: dict[str, list[str]]) -> tuple[list, str | None, bool]:
    limit, offset = _page_window(query)
    page = items[offset : offset + limit]
    has_more = offset + limit < len(items)
    return page, _encode_cursor(offset + limit) if has_more else None, has_more


class AgentWebHandler(BaseHTTPRequestHandler):
    server_version = "AgentWeb/0.10.0"

    @property
    def engine(self) -> AgentWebEngine:
        return self.server.engine  # type: ignore[attr-defined]

    @property
    def authenticator(self) -> Authenticator:
        return self.server.authenticator  # type: ignore[attr-defined]

    @property
    def rate_limiter(self) -> RateLimiter:
        return self.server.rate_limiter  # type: ignore[attr-defined]

    @property
    def metrics(self):
        return self.server.engine.metrics  # type: ignore[attr-defined]

    def handle_one_request(self) -> None:  # noqa: N802
        started = time.monotonic()
        try:
            super().handle_one_request()
        finally:
            endpoint, _ = _normalize_api_path(urlparse(getattr(self, "path", "/unknown")).path)
            org_id = getattr(getattr(self, "_principal", None), "org_id", None)
            self.metrics.record_request(endpoint, time.monotonic() - started, int(getattr(self, "_last_response_status", 500)), org_id, getattr(self, "_last_error_type", None))

    @property
    def principal(self):
        return getattr(self, "_principal", None)

    def _response_metadata(self, request_id: str | None) -> dict[str, object]:
        return {
            "request_id": request_id,
            "api_version": "v1",
            "path": getattr(self, "_canonical_api_path", "/v1"),
            "deprecated": bool(getattr(self, "_legacy_api_path", False)),
        }

    def _decorate_success_payload(self, payload: dict | list | None, request_id: str | None) -> dict | list | None:
        if not isinstance(payload, dict) or "error" in payload:
            return payload
        decorated = dict(payload)
        decorated["_meta"] = self._response_metadata(request_id)
        return decorated

    def _send_json(self, status: int, payload: dict | list | None = None, request_id: str | None = None) -> None:
        payload = self._decorate_success_payload(payload, request_id) if status != HTTPStatus.NO_CONTENT else payload
        body = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._last_response_status = int(status)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        allowed_origins = {item.strip() for item in os.getenv("AGENTWEB_ALLOWED_ORIGINS", "").split(",") if item.strip()}
        origin = self.headers.get("Origin")
        if allowed_origins:
            if origin in allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
        elif not self.authenticator.key_store.has_active_keys() and not self.authenticator._keys:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        rate_info = getattr(self, "_rate_limit_info", None)
        if rate_info:
            self.send_header("X-RateLimit-Limit", str(int(rate_info["limit"])))
            self.send_header("X-RateLimit-Remaining", str(int(float(rate_info["remaining"]))))
            self.send_header("X-RateLimit-Reset", str(int(rate_info["reset"])))
        if status == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after = getattr(getattr(self, "_rate_limit_error", None), "retry_after", None)
            if retry_after is not None:
                self.send_header("Retry-After", str(int(retry_after)))
        if request_id:
            self.send_header("X-Request-ID", request_id)
        self.send_header("X-AgentWeb-API-Version", "v1")
        if getattr(self, "_legacy_api_path", False):
            self.send_header("Deprecation", "true")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _error(self, error: AgentWebError, request_id: str) -> None:
        self._last_error_type = error.error_type
        error.request_id = request_id
        self._send_json(error.status_code, error.as_dict(), request_id)

    def _authenticate(self, scope: str, request_id: str):
        try:
            principal = self.authenticator.authenticate(self.headers.get("Authorization"), scope)
            if scope == "admin:*" and not principal.authenticated:
                raise PermissionError("admin endpoints require an authenticated organization key")
            weight = 2.0 if scope == "solve:execute" else 1.0
            self._rate_limit_info = self.rate_limiter.check(f"{principal.org_id}:{principal.key_id}", weight)
            self._principal = principal
            return principal
        except AgentWebError as error:
            if error.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                self._rate_limit_error = error
                retry_after = getattr(error, "retry_after", 60) or 60
                self._rate_limit_info = {"limit": self.rate_limiter.capacity, "remaining": 0, "reset": int(time.time()) + int(retry_after)}
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

    def _idempotency_key(self, payload: dict | None = None) -> str | None:
        payload = payload or {}
        value = payload.get("idempotency_key") or self.headers.get("Idempotency-Key")
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip() or len(value) > 128:
            raise InvalidRequestError("idempotency_key must be a non-empty string up to 128 characters")
        return value.strip()

    def _begin_idempotency(self, principal, key: str | None, payload: dict) -> tuple[str | None, str | None]:
        if key is None:
            return None, None
        semantic_payload = {name: value for name, value in payload.items() if name != "idempotency_key"}
        request_hash = _request_hash(semantic_payload)
        existing = self.engine.memory.claim_idempotency(principal.org_id, key, request_hash)
        if existing:
            if existing["request_hash"] != request_hash:
                raise ConflictError("idempotency key was already used with a different request")
            if existing["status"] == "completed":
                body = json.loads(existing.get("response_body") or "null")
                if isinstance(body, dict):
                    body.pop("_meta", None)
                self._send_json(int(existing["response_status"]), body, "req_replay_" + uuid.uuid4().hex[:12])
                return key, None
            raise ConflictError("idempotency key is already being processed")
        return key, request_hash

    def _complete_idempotency(self, principal, key: str | None, request_hash: str | None, status: int, payload: dict | list | None) -> None:
        if key and request_hash:
            body = "" if payload is None else json.dumps(payload, ensure_ascii=False)
            self.engine.memory.complete_idempotency(principal.org_id, key, request_hash, status, body)

    def _release_idempotency(self, principal, key: str | None, request_hash: str | None) -> None:
        if key and request_hash:
            self.engine.memory.release_idempotency(principal.org_id, key, request_hash)

    def _health_payload(self) -> dict[str, object]:
        checks: dict[str, str] = {}

        def check(name: str, probe) -> None:
            try:
                checks[name] = "ok" if probe() else "failed"
            except Exception:
                checks[name] = "failed"

        check("memory", self.engine.memory.health)
        check("metrics", self.metrics.health)
        check("audit", self.server.authenticator.key_store.health)  # type: ignore[attr-defined]
        coordinator = getattr(self.server, "queue_coordinator", None)
        if coordinator is None:
            checks["queue"] = "disabled"
        else:
            check("queue", getattr(coordinator, "health", lambda: False))
        healthy = all(value in {"ok", "disabled"} for value in checks.values())
        return {"status": "ok" if healthy else "degraded", "service": "agentweb", "checks": checks}

    def do_OPTIONS(self) -> None:  # noqa: N802
        path, versioned = _normalize_api_path(urlparse(self.path).path)
        self._legacy_api_path = not versioned
        self._canonical_api_path = "/v1" if path == "/" else "/v1" + path
        self._send_json(HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:  # noqa: N802
        request_id = "req_" + uuid.uuid4().hex[:16]
        parsed_url = urlparse(self.path)
        path, versioned = _normalize_api_path(parsed_url.path)
        self._legacy_api_path = not versioned
        self._canonical_api_path = "/v1" if path == "/" else "/v1" + path
        query = parse_qs(parsed_url.query)
        if path == "/health":
            payload = self._health_payload()
            status = HTTPStatus.OK if payload["status"] == "ok" else HTTPStatus.SERVICE_UNAVAILABLE
            self._send_json(status, payload, request_id)
            return
        if path.startswith("/admin/"):
            scope = "admin:*"
        elif path.startswith(("/memory/", "/report/")):
            scope = "memory:read"
        elif path.startswith("/graph"):
            scope = "graph:read"
        elif path.startswith("/workflows"):
            scope = "workflow:manage"
        elif path.startswith("/learning"):
            scope = "learning:read"
        elif path.startswith("/crawl"):
            scope = "search:read"
        else:
            scope = "observe:manage"
        principal = self._authenticate(scope, request_id)
        if principal is None:
            return
        try:
            if path == "/crawl":
                limit, offset = _page_window(query)
                candidates = self.engine.memory.list_crawls(principal.org_id, limit=limit + 1, offset=offset)
                crawls = candidates[:limit]
                has_more = len(candidates) > limit
                next_cursor = _encode_cursor(offset + limit) if has_more else None
                self._send_json(HTTPStatus.OK, {"data": crawls, "crawls": crawls, "next_cursor": next_cursor, "has_more": has_more}, request_id)
                return
            if path.startswith("/crawl/"):
                crawl_id = path.rsplit("/", 1)[-1]
                crawl = self.engine.memory.get_crawl(crawl_id, principal.org_id)
                if not crawl:
                    raise NotFoundError("crawl not found")
                pages = self.engine.memory.list_crawl_pages(crawl_id, principal.org_id, limit=100)
                self._send_json(HTTPStatus.OK, {**crawl, "pages": pages, "data": pages}, request_id)
                return
            if path == "/graph/query":
                limit, offset = _page_window(query)
                try:
                    depth = int(query.get("depth", ["1"])[0])
                except (TypeError, ValueError):
                    raise InvalidRequestError("depth must be an integer between 1 and 3")
                if depth < 1 or depth > 3:
                    raise InvalidRequestError("depth must be an integer between 1 and 3")
                graph_result = self.engine.graph.query(
                    entity_type=_query_value(query, "entity_type"),
                    related_to=_query_value(query, "related_to"),
                    relation=_query_value(query, "relation"),
                    org_id=principal.org_id,
                    limit=limit,
                    depth=depth,
                    cursor=offset,
                )
                graph_payload = graph_result.to_dict()
                graph_payload["next_cursor"] = _encode_cursor(offset + limit) if graph_result.has_more else None
                self._send_json(HTTPStatus.OK, self._decorate_success_payload(graph_payload, request_id), request_id)
                return
            if path == "/learning/summary":
                summaries = self.engine.learning.summary(principal.org_id, _page_window(query)[0])
                self._send_json(HTTPStatus.OK, self._decorate_success_payload({"strategies": summaries, "data": summaries}, request_id), request_id)
                return
            if path == "/workflows":
                workflows, next_cursor, has_more = _page(self.engine.workflows.list(principal.org_id), query)
                self._send_json(HTTPStatus.OK, self._decorate_success_payload({"workflows": workflows, "data": workflows, "next_cursor": next_cursor, "has_more": has_more}, request_id), request_id)
                return
            if path == "/workflows/runs":
                limit, _ = _page_window(query)
                runs = self.engine.workflows.list_runs(principal.org_id, limit=limit)
                self._send_json(HTTPStatus.OK, self._decorate_success_payload({"runs": runs, "data": runs}, request_id), request_id)
                return
            if path == "/observe":
                monitors, next_cursor, has_more = _page(self.engine.memory.list_monitors(principal.org_id), query)
                self._send_json(HTTPStatus.OK, {"data": monitors, "monitors": monitors, "next_cursor": next_cursor, "has_more": has_more}, request_id)
                return
            if path.startswith("/observe/"):
                monitor_id = path.rsplit("/", 1)[-1]
                monitor = self.engine.memory.get_monitor(monitor_id, principal.org_id)
                if not monitor:
                    raise NotFoundError("monitor not found")
                self._send_json(HTTPStatus.OK, self.engine.check_monitor(monitor).to_dict(), request_id)
                return
            if path.startswith("/report/"):
                report_target = path[len("/report/") :].strip("/")
                replay = report_target.endswith("/replay")
                execution_id = report_target[: -len("/replay")].rstrip("/") if replay else report_target
                payload = self.engine.traces.replay(execution_id, principal.org_id) if replay else self.engine.traces.get(execution_id, principal.org_id)
                if not payload:
                    raise NotFoundError("execution trace not found")
                self._send_json(HTTPStatus.OK, payload, request_id)
                return
            if path.startswith("/memory/"):
                target_part = path[len("/memory/") :]
                if target_part.endswith("/diff"):
                    target = unquote(target_part[: -len("/diff")].rstrip("/"))
                    from_hash = query.get("from", [""])[0]
                    to_hash = query.get("to", [""])[0]
                    if not from_hash or not to_hash:
                        raise InvalidRequestError("memory diff requires from and to query parameters")
                    try:
                        payload = self.engine.memory.diff(target, from_hash, to_hash, principal.org_id)
                    except KeyError as error:
                        raise NotFoundError(str(error)) from error
                    self._send_json(HTTPStatus.OK, payload, request_id)
                    return
                target = unquote(target_part)
                snapshots, next_cursor, has_more = _page(self.engine.memory.list_snapshots(target, principal.org_id), query)
                self._send_json(
                    HTTPStatus.OK,
                    {"org_id": principal.org_id, "target": target, "snapshots": snapshots, "data": snapshots, "next_cursor": next_cursor, "has_more": has_more},
                    request_id,
                )
                return
            if path == "/admin/keys":
                keys, next_cursor, has_more = _page(self.authenticator.key_store.list_keys(principal.org_id), query)
                self._send_json(HTTPStatus.OK, {"keys": keys, "data": keys, "next_cursor": next_cursor, "has_more": has_more}, request_id)
                return
            if path == "/admin/browser-credentials":
                credentials, next_cursor, has_more = _page(self.engine.credentials.list(principal.org_id), query)
                self._send_json(HTTPStatus.OK, {"credentials": credentials, "data": credentials, "next_cursor": next_cursor, "has_more": has_more}, request_id)
                return
            if path == "/admin/browser-session-states":
                states, next_cursor, has_more = _page(self.engine.session_states.list(principal.org_id), query)
                self._send_json(HTTPStatus.OK, {"session_states": states, "data": states, "next_cursor": next_cursor, "has_more": has_more}, request_id)
                return
            if path == "/admin/audit":
                since = _parse_audit_timestamp(query, "since")
                until = _parse_audit_timestamp(query, "until")
                if since is not None and until is not None and since > until:
                    raise InvalidRequestError("since must be earlier than or equal to until")
                limit, offset = _page_window(query)
                events, has_more = self.authenticator.key_store.list_audit_page(
                    principal.org_id,
                    limit=limit,
                    offset=offset,
                    action=_audit_filter(query, "action"),
                    actor=_audit_filter(query, "actor"),
                    target=_audit_filter(query, "target"),
                    since=since,
                    until=until,
                )
                next_cursor = _encode_cursor(offset + limit) if has_more else None
                self._send_json(HTTPStatus.OK, {"events": events, "data": events, "next_cursor": next_cursor, "has_more": has_more}, request_id)
                return
            if path == "/admin/metrics":
                metrics = self.metrics.snapshot(principal.org_id)
                queue_store = self.engine.scheduler.queue_store
                metrics["gauges"].update({f"queue_{key}": value for key, value in queue_store.queue_summary(principal.org_id).items()})
                self._send_json(HTTPStatus.OK, metrics, request_id)
                return
            if path == "/admin/usage":
                period = query.get("period", [None])[0]
                if period is not None and not re.fullmatch(r"\d{4}-\d{2}", period):
                    raise InvalidRequestError("period must use YYYY-MM format")
                self._send_json(HTTPStatus.OK, self.engine.memory.usage_summary(principal.org_id, period), request_id)
                return
            raise NotFoundError("route not found")
        except AgentWebError as error:
            self._error(error, request_id)

    def do_DELETE(self) -> None:  # noqa: N802
        request_id = "req_" + uuid.uuid4().hex[:16]
        path, versioned = _normalize_api_path(urlparse(self.path).path)
        self._legacy_api_path = not versioned
        self._canonical_api_path = "/v1" if path == "/" else "/v1" + path
        scope = "admin:*" if path.startswith(("/admin/keys/", "/admin/browser-credentials/", "/admin/browser-session-states/", "/admin/data")) else "observe:manage"
        principal = self._authenticate(scope, request_id)
        if principal is None:
            return
        idempotency_key = None
        request_hash = None
        try:
            payload = self._read_json() if path == "/admin/data" else {}
            if path.startswith(("/admin/keys/", "/admin/browser-credentials/", "/admin/browser-session-states/", "/observe/")) or path == "/admin/data":
                idempotency_key, request_hash = self._begin_idempotency(principal, self._idempotency_key(payload), payload)
                if idempotency_key and request_hash is None:
                    return
            if path == "/admin/data":
                kind = payload.get("kind", "snapshots")
                if kind not in {"snapshots", "traces", "crawls", "session_states", "all"}:
                    raise InvalidRequestError("kind must be snapshots, traces, crawls, session_states, or all")
                target = payload.get("target")
                if target is not None and (not isinstance(target, str) or not target.strip()):
                    raise InvalidRequestError("target must be a non-empty string when provided")
                execution_id = payload.get("execution_id")
                if execution_id is not None and (not isinstance(execution_id, str) or not execution_id.strip()):
                    raise InvalidRequestError("execution_id must be a non-empty string when provided")
                deleted_snapshots = self.engine.memory.delete_snapshots(principal.org_id, redact_url(target) if target and target.startswith(("http://", "https://")) else target) if kind in {"snapshots", "all"} else 0
                deleted_traces = self.engine.traces.delete(principal.org_id, execution_id) if kind in {"traces", "all"} else 0
                deleted_crawls = self.engine.memory.delete_crawls(principal.org_id) if kind in {"crawls", "all"} else 0
                deleted_session_states = self.engine.session_states.delete_all(principal.org_id) if kind in {"session_states", "all"} else 0
                self.authenticator.key_store.audit(principal.org_id, principal.key_id, "data.deletion_requested", principal.org_id, {"kind": kind, "target": redact_url(target) if isinstance(target, str) else target, "execution_id": execution_id, "deleted_snapshots": deleted_snapshots, "deleted_traces": deleted_traces, "deleted_crawls": deleted_crawls, "deleted_session_states": deleted_session_states})
                response_payload = {"org_id": principal.org_id, "kind": kind, "deleted_snapshots": deleted_snapshots, "deleted_traces": deleted_traces, "deleted_crawls": deleted_crawls, "deleted_session_states": deleted_session_states}
                response_payload = self._decorate_success_payload(response_payload, request_id)
                self._complete_idempotency(principal, idempotency_key, request_hash, int(HTTPStatus.OK), response_payload)
                self._send_json(HTTPStatus.OK, response_payload, request_id)
                return
            if path.startswith("/admin/keys/"):
                key_id = path.rsplit("/", 1)[-1]
                if not self.authenticator.revoke_key(principal.org_id, key_id, principal.key_id):
                    raise NotFoundError("API key not found")
                self._complete_idempotency(principal, idempotency_key, request_hash, int(HTTPStatus.NO_CONTENT), None)
                self._send_json(HTTPStatus.NO_CONTENT, request_id=request_id)
                return
            if path.startswith("/admin/browser-credentials/"):
                credential_id = path.rsplit("/", 1)[-1]
                if not self.engine.credentials.revoke(principal.org_id, credential_id, principal.key_id):
                    raise NotFoundError("browser credential not found")
                self._complete_idempotency(principal, idempotency_key, request_hash, int(HTTPStatus.NO_CONTENT), None)
                self._send_json(HTTPStatus.NO_CONTENT, request_id=request_id)
                return
            if path.startswith("/admin/browser-session-states/"):
                state_id = path.rsplit("/", 1)[-1]
                if not self.engine.session_states.revoke(principal.org_id, state_id, principal.key_id):
                    raise NotFoundError("browser session state not found")
                self._complete_idempotency(principal, idempotency_key, request_hash, int(HTTPStatus.NO_CONTENT), None)
                self._send_json(HTTPStatus.NO_CONTENT, request_id=request_id)
                return
            if path.startswith("/observe/"):
                monitor_id = path.rsplit("/", 1)[-1]
                if not self.engine.memory.delete_monitor(monitor_id, principal.org_id):
                    raise NotFoundError("monitor not found")
                self._complete_idempotency(principal, idempotency_key, request_hash, int(HTTPStatus.NO_CONTENT), None)
                self._send_json(HTTPStatus.NO_CONTENT, request_id=request_id)
                return
            raise NotFoundError("route not found")
        except AgentWebError as error:
            self._release_idempotency(principal, idempotency_key, request_hash)
            self._error(error, request_id)
        except Exception:
            self._release_idempotency(principal, idempotency_key, request_hash)
            self._error(AgentWebError("internal server error", request_id=request_id), request_id)

    def do_POST(self) -> None:  # noqa: N802
        request_id = "req_" + uuid.uuid4().hex[:16]
        path, versioned = _normalize_api_path(urlparse(self.path).path)
        self._legacy_api_path = not versioned
        self._canonical_api_path = "/v1" if path == "/" else "/v1" + path
        scope = {
            "/solve": "solve:execute",
            "/plan": "solve:execute",
            "/execute": "solve:execute",
            "/observe": "observe:manage",
            "/search": "search:read",
            "/extract": "extract:read",
            "/crawl": "search:read",
            "/graph/entities": "graph:write",
            "/graph/relations": "graph:write",
            "/workflows": "workflow:manage",
            "/learning/outcomes": "learning:write",
            "/browser/sessions": "browser:execute",
            "/admin/keys": "admin:*",
            "/admin/browser-credentials": "admin:*",
            "/admin/browser-session-states": "admin:*",
        }.get(path)
        if scope is None:
            self._error(NotFoundError("route not found"), request_id)
            return
        principal = self._authenticate(scope, request_id)
        if principal is None:
            return
        idempotency_key = None
        request_hash = None
        try:
            payload = self._read_json()
            if path in {"/solve", "/execute", "/observe", "/crawl", "/graph/entities", "/graph/relations", "/workflows", "/learning/outcomes"} or path in {"/workflows/pause", "/workflows/resume"} or path.startswith(("/admin/keys", "/admin/browser-credentials", "/admin/browser-session-states")):
                idempotency_key, request_hash = self._begin_idempotency(principal, self._idempotency_key(payload), payload)
                if idempotency_key and request_hash is None:
                    return
            response_status = HTTPStatus.OK
            response_payload: dict | list | None
            if path == "/plan":
                response_payload = self.engine.create_plan(
                    payload.get("task", ""),
                    payload.get("mode"),
                    principal.org_id,
                    payload.get("skill"),
                    payload.get("inputs"),
                )
            elif path == "/execute":
                response_payload = self.engine.execute_plan(
                    payload.get("plan_id", ""),
                    principal.org_id,
                    payload.get("output_format"),
                )
            elif path == "/solve":
                solve_inputs = payload.get("inputs")
                if "graph_query" in payload:
                    if solve_inputs is None:
                        solve_inputs = {}
                    if not isinstance(solve_inputs, dict):
                        raise InvalidRequestError("inputs must be an object when graph_query is provided")
                    solve_inputs = {**solve_inputs, "graph_query": payload.get("graph_query")}
                response_payload = self.engine.solve(
                    payload.get("task", ""),
                    payload.get("mode"),
                    principal.org_id,
                    payload.get("output_format"),
                    payload.get("skill"),
                    solve_inputs,
                ).to_dict()
            elif path == "/observe":
                monitor = self.engine.create_monitor(
                    payload.get("task", ""), payload.get("frequency", "hourly"), payload.get("webhook_url"), principal.org_id,
                    change_policy=payload.get("change_policy"),
                )
                response_payload = monitor.to_dict()
            elif path == "/search":
                query = payload.get("query", "")
                response_payload = {"query": query, "results": search(query, payload.get("limit", 10), payload.get("freshness"), self.engine.search_provider)}
            elif path == "/extract":
                response_payload = self.engine.extract(payload.get("url", ""), payload.get("schema"), principal.org_id)
            elif path == "/crawl":
                result = self.engine.crawler.crawl(
                    payload.get("start_url", ""), payload.get("max_pages", 50), payload.get("depth", 2), payload.get("url_pattern"), principal.org_id
                )
                response_payload = result.to_dict()
            elif path == "/graph/entities":
                response_status = HTTPStatus.CREATED
                response_payload = self.engine.graph.upsert_entity(payload, principal.org_id).to_dict()
            elif path == "/graph/relations":
                response_status = HTTPStatus.CREATED
                response_payload = self.engine.graph.upsert_relation(
                    payload.get("from_id", payload.get("from", "")),
                    payload.get("to_id", payload.get("to", "")),
                    payload.get("relation", payload.get("type", "")),
                    payload.get("confidence", 0.5),
                    principal.org_id,
                    payload.get("source_ids", payload.get("source_id")),
                ).to_dict()
            elif path == "/learning/outcomes":
                response_status = HTTPStatus.CREATED
                response_payload = self.engine.learning.record_outcome(
                    strategy=payload.get("strategy", payload.get("skill", "")),
                    mode=payload.get("mode", "focus"),
                    success=payload.get("success", False),
                    evidence_score=payload.get("evidence_score", 0.0),
                    org_id=principal.org_id,
                    execution_id=payload.get("execution_id"),
                    latency_ms=payload.get("latency_ms"),
                )
            elif path in {"/workflows/pause", "/workflows/resume"}:
                workflow_id = str(payload.get("workflow_id", "")).strip()
                response_payload = self.engine.workflows.set_status(workflow_id, "paused" if path.endswith("/pause") else "active", principal.org_id)
            elif path == "/workflows":
                response_status = HTTPStatus.CREATED
                response_payload = self.engine.workflows.create(
                    name=payload.get("name", ""),
                    monitor_id=payload.get("monitor_id", ""),
                    task_template=payload.get("task_template", payload.get("task", "")),
                    event=payload.get("event", "monitor.change_detected"),
                    mode=payload.get("mode", "focus"),
                    org_id=principal.org_id,
                )
            elif path == "/browser/sessions":
                session = self.engine.browser_open(payload.get("url", ""), payload.get("actions", []), principal.org_id, payload.get("credential_id"), payload.get("session_state_id"))
                response_payload = session.to_dict()
            elif path == "/admin/browser-session-states":
                response_status = HTTPStatus.CREATED
                response_payload = self.engine.session_states.create(
                    principal.org_id,
                    payload.get("label"),
                    payload.get("origin"),
                    payload.get("state"),
                    principal.key_id,
                )
            elif path == "/admin/browser-credentials":
                response_status = HTTPStatus.CREATED
                response_payload = self.engine.credentials.create(
                    principal.org_id,
                    payload.get("label"),
                    payload.get("username"),
                    payload.get("secret"),
                    principal.key_id,
                )
            else:
                response_status = HTTPStatus.CREATED
                response_payload = self.authenticator.key_store.create_key(principal.org_id, payload.get("scopes", []), principal.key_id)
            response_payload = self._decorate_success_payload(response_payload, request_id)
            self._complete_idempotency(principal, idempotency_key, request_hash, int(response_status), response_payload)
            self._send_json(response_status, response_payload, request_id)
        except AgentWebError as error:
            self._release_idempotency(principal, idempotency_key, request_hash)
            self._error(error, request_id)
        except (ValueError, TypeError) as error:
            self._release_idempotency(principal, idempotency_key, request_hash)
            self._error(InvalidRequestError(str(error)), request_id)
        except RuntimeError as error:
            self._release_idempotency(principal, idempotency_key, request_hash)
            from .errors import UpstreamError
            self._error(UpstreamError(str(error)), request_id)
        except Exception:  # defensive API boundary; details stay local
            self._release_idempotency(principal, idempotency_key, request_hash)
            self._error(AgentWebError("internal server error", request_id=request_id), request_id)

    def log_message(self, format: str, *args: object) -> None:
        if os.getenv("AGENTWEB_QUIET") != "1":
            super().log_message(format, *args)


def create_server(host: str = "127.0.0.1", port: int = 8000, data_path: str = "agentweb.sqlite3"):
    from .memory import MemoryStore

    server = ThreadingHTTPServer((host, port), AgentWebHandler)
    store = MemoryStore(data_path)
    provider = build_provider()
    coordinator = open_distributed_queue(DatabaseConfig.from_environment(provider))
    server.engine = AgentWebEngine(store, secret_provider=provider, queue_coordinator=coordinator)  # type: ignore[attr-defined]
    server.queue_coordinator = coordinator  # type: ignore[attr-defined]
    server.authenticator = Authenticator(data_path, provider=provider)  # type: ignore[attr-defined]
    server.rate_limiter = RateLimiter()  # type: ignore[attr-defined]
    return server
