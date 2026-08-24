"""Tenant-aware authentication, key lifecycle, auditing, and rate limiting."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
import math
import uuid
from dataclasses import dataclass
from pathlib import Path

from .errors import AuthenticationError, InvalidRequestError, PermissionError, RateLimitError
from .secrets import SecretProvider, build_provider


ALL_SCOPES = {
    "search:read",
    "extract:read",
    "browser:execute",
    "solve:execute",
    "observe:manage",
    "memory:read",
    "graph:read",
    "admin:*",
}


@dataclass(frozen=True)
class Principal:
    key_id: str
    org_id: str
    scopes: frozenset[str]
    authenticated: bool = True


class KeyStore:
    """SQLite key store that persists only salted password-derived key hashes."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS api_keys (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    prefix TEXT NOT NULL,
                    hashed_secret TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    revoked_at REAL
                );
                CREATE INDEX IF NOT EXISTS idx_api_keys_org ON api_keys(org_id, revoked_at);
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    metadata TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_org_time_id ON audit_events(org_id, timestamp DESC, id DESC);
                CREATE INDEX IF NOT EXISTS idx_audit_org_action_time ON audit_events(org_id, action, timestamp DESC, id DESC);
                CREATE INDEX IF NOT EXISTS idx_audit_org_actor_time ON audit_events(org_id, actor, timestamp DESC, id DESC);
                CREATE INDEX IF NOT EXISTS idx_audit_org_target_time ON audit_events(org_id, target, timestamp DESC, id DESC);
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO organizations(id, name, created_at) VALUES (?, ?, ?)",
                ("development", "Local development", time.time()),
            )

    def health(self) -> bool:
        try:
            with self._connect() as connection:
                return connection.execute("SELECT 1").fetchone()[0] == 1
        except sqlite3.Error:
            return False

    @staticmethod
    def _hash_secret(secret: str, salt: bytes | None = None) -> str:
        salt = salt or secrets.token_bytes(16)
        derived = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, 120_000)
        return f"{salt.hex()}${derived.hex()}"

    @staticmethod
    def _verify_secret(secret: str, encoded: str) -> bool:
        try:
            salt_hex, digest_hex = encoded.split("$", 1)
            expected = KeyStore._hash_secret(secret, bytes.fromhex(salt_hex)).split("$", 1)[1]
            return hmac.compare_digest(expected, digest_hex)
        except (ValueError, TypeError):
            return False

    def ensure_org(self, org_id: str, name: str | None = None) -> None:
        org_id = self._validate_org_id(org_id)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO organizations(id, name, created_at) VALUES (?, ?, ?)",
                (org_id, name or org_id, time.time()),
            )

    @staticmethod
    def _validate_org_id(org_id: str) -> str:
        value = str(org_id or "").strip()
        if not value or len(value) > 100 or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in value):
            raise InvalidRequestError("org_id must contain only letters, numbers, underscores, or hyphens")
        return value

    @staticmethod
    def _validate_scopes(scopes: list[str] | tuple[str, ...] | set[str]) -> frozenset[str]:
        if not isinstance(scopes, (list, tuple, set)):
            raise InvalidRequestError("scopes must be a JSON array")
        normalized = frozenset(str(scope).strip() for scope in scopes)
        unknown = normalized - ALL_SCOPES
        if unknown:
            raise InvalidRequestError(f"unknown API key scope: {sorted(unknown)[0]}")
        if not normalized:
            raise InvalidRequestError("at least one API key scope is required")
        return normalized

    def create_key(self, org_id: str, scopes: list[str], actor: str = "system") -> dict:
        org_id = self._validate_org_id(org_id)
        normalized = self._validate_scopes(scopes)
        self.ensure_org(org_id)
        secret = "sk-live-" + secrets.token_urlsafe(32)
        key_id = "key_" + uuid.uuid4().hex[:16]
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO api_keys(id, org_id, scope, prefix, hashed_secret, created_at, revoked_at) "
                "VALUES (?, ?, ?, ?, ?, ?, NULL)",
                (key_id, org_id, json.dumps(sorted(normalized)), secret[:16], self._hash_secret(secret), now),
            )
        self.audit(org_id, actor, "api_key.created", key_id, {"scopes": sorted(normalized)})
        return {"id": key_id, "org_id": org_id, "scopes": sorted(normalized), "secret": secret, "created_at": now}

    def authenticate(self, token: str) -> Principal | None:
        prefix = token[:16]
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, org_id, scope, hashed_secret FROM api_keys "
                "WHERE prefix = ? AND revoked_at IS NULL LIMIT 5",
                (prefix,),
            ).fetchall()
        for row in rows:
            if self._verify_secret(token, row["hashed_secret"]):
                return Principal(row["id"], row["org_id"], frozenset(json.loads(row["scope"])))
        return None

    def has_active_keys(self) -> bool:
        with self._connect() as connection:
            return connection.execute("SELECT 1 FROM api_keys WHERE revoked_at IS NULL LIMIT 1").fetchone() is not None

    def list_keys(self, org_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, org_id, scope, prefix, created_at, revoked_at FROM api_keys WHERE org_id=? ORDER BY created_at DESC",
                (org_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "org_id": row["org_id"],
                "scopes": json.loads(row["scope"]),
                "prefix": row["prefix"],
                "created_at": row["created_at"],
                "revoked_at": row["revoked_at"],
            }
            for row in rows
        ]

    def revoke_key(self, org_id: str, key_id: str, actor: str) -> bool:
        now = time.time()
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE api_keys SET revoked_at=? WHERE id=? AND org_id=? AND revoked_at IS NULL",
                (now, key_id, org_id),
            )
        if cursor.rowcount:
            self.audit(org_id, actor, "api_key.revoked", key_id, {})
            return True
        return False

    def audit(self, org_id: str, actor: str, action: str, target: str, metadata: dict) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO audit_events(id, org_id, actor, action, target, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("aud_" + uuid.uuid4().hex[:16], org_id, actor[:100], action[:100], target[:200], time.time(), json.dumps(metadata, separators=(",", ":"))),
            )

    @staticmethod
    def _audit_event(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "org_id": row["org_id"],
            "actor": row["actor"],
            "action": row["action"],
            "target": row["target"],
            "timestamp": row["timestamp"],
            "metadata": json.loads(row["metadata"]),
        }

    @staticmethod
    def _audit_query(
        org_id: str,
        action: str | None = None,
        actor: str | None = None,
        target: str | None = None,
        since: float | None = None,
        until: float | None = None,
    ) -> tuple[list[str], list[object]]:
        clauses = ["org_id=?"]
        parameters: list[object] = [org_id]
        for column, value in (("action", action), ("actor", actor), ("target", target)):
            if value is not None:
                clauses.append(f"{column}=?")
                parameters.append(value)
        if since is not None:
            clauses.append("timestamp>=?")
            parameters.append(float(since))
        if until is not None:
            clauses.append("timestamp<=?")
            parameters.append(float(until))
        return clauses, parameters

    def list_audit(
        self,
        org_id: str,
        limit: int = 10_000,
        *,
        action: str | None = None,
        actor: str | None = None,
        target: str | None = None,
        since: float | None = None,
        until: float | None = None,
    ) -> list[dict]:
        limit = max(1, min(int(limit), 10_000))
        clauses, parameters = self._audit_query(org_id, action, actor, target, since, until)
        parameters.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, org_id, actor, action, target, timestamp, metadata FROM audit_events "
                f"WHERE {' AND '.join(clauses)} ORDER BY timestamp DESC, id DESC LIMIT ?",
                parameters,
            ).fetchall()
        return [self._audit_event(row) for row in rows]

    def list_audit_page(
        self,
        org_id: str,
        limit: int = 50,
        offset: int = 0,
        *,
        action: str | None = None,
        actor: str | None = None,
        target: str | None = None,
        since: float | None = None,
        until: float | None = None,
    ) -> tuple[list[dict], bool]:
        limit = max(1, min(int(limit), 100))
        offset = max(0, int(offset))
        clauses, parameters = self._audit_query(org_id, action, actor, target, since, until)
        parameters.extend((limit + 1, offset))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, org_id, actor, action, target, timestamp, metadata FROM audit_events "
                f"WHERE {' AND '.join(clauses)} ORDER BY timestamp DESC, id DESC LIMIT ? OFFSET ?",
                parameters,
            ).fetchall()
        has_more = len(rows) > limit
        return [self._audit_event(row) for row in rows[:limit]], has_more

    def purge_expired_audit(self, retention_seconds: float, now: float | None = None, org_id: str | None = None) -> int:
        if retention_seconds < 0:
            raise ValueError("audit retention cannot be negative")
        cutoff = (time.time() if now is None else now) - retention_seconds
        clauses = ["timestamp < ?"]
        parameters: list[object] = [cutoff]
        if org_id is not None:
            clauses.append("org_id = ?")
            parameters.append(org_id)
        with self._connect() as connection:
            cursor = connection.execute(f"DELETE FROM audit_events WHERE {' AND '.join(clauses)}", parameters)
        return cursor.rowcount


class Authenticator:
    """Authenticate environment or durable keys and return a tenant-scoped principal."""

    def __init__(self, path: str | Path | None = None, provider: SecretProvider | None = None) -> None:
        self.key_store = KeyStore(path or os.getenv("AGENTWEB_DATA_PATH", "agentweb.sqlite3"))
        self.secret_provider = provider or build_provider()
        self._keys = self._load_keys(self.secret_provider)
        self._cache: dict[str, tuple[float, Principal]] = {}
        self._cache_ttl = 5.0

    @staticmethod
    def _load_keys(provider: SecretProvider) -> dict[str, tuple[str, frozenset[str]]]:
        configured: dict[str, tuple[str, frozenset[str]]] = {}
        default_org = os.getenv("AGENTWEB_API_KEY_ORG", "env")
        single = provider.get("AGENTWEB_API_KEY", required=False)
        if single:
            configured[single] = (default_org, frozenset(ALL_SCOPES))
        raw = provider.get("AGENTWEB_API_KEYS", required=False)
        if raw:
            try:
                decoded = json.loads(raw)
                if isinstance(decoded, dict):
                    for key, value in decoded.items():
                        org_id = default_org
                        scopes = value
                        if isinstance(value, dict):
                            scopes = value.get("scopes", [])
                            org_id = str(value.get("org_id", default_org))
                        if isinstance(scopes, str):
                            scopes = [scopes]
                        if isinstance(scopes, list):
                            configured[str(key)] = (org_id, frozenset(str(scope) for scope in scopes))
            except json.JSONDecodeError:
                pass
        return configured

    def revoke_key(self, org_id: str, key_id: str, actor: str) -> bool:
        revoked = self.key_store.revoke_key(org_id, key_id, actor)
        if revoked:
            self._cache.clear()
        return revoked

    def authenticate(self, authorization: str | None, required_scope: str) -> Principal:
        configured_mode = bool(self._keys) or self.key_store.has_active_keys()
        if not configured_mode:
            return Principal("development", "development", frozenset(ALL_SCOPES), authenticated=False)
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthenticationError("missing or invalid bearer API key")
        token = authorization[7:].strip()
        env_record = self._keys.get(token)
        if env_record:
            principal = Principal(token[:8], env_record[0], env_record[1])
        else:
            cached = self._cache.get(token)
            if cached and cached[0] > time.monotonic():
                principal = cached[1]
            else:
                principal = self.key_store.authenticate(token)
                if principal is not None:
                    self._cache[token] = (time.monotonic() + self._cache_ttl, principal)
        if principal is None:
            raise AuthenticationError("missing or invalid bearer API key")
        if required_scope not in principal.scopes and "admin:*" not in principal.scopes:
            raise PermissionError(f"API key lacks required scope: {required_scope}")
        return principal


class RateLimiter:
    """Process-local token buckets partitioned by tenant/key and execution class."""

    def __init__(self, capacity: float = 100.0, refill_per_second: float = 100.0 / 60.0) -> None:
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def check(self, key_id: str, weight: float = 1.0, bucket: str = "interactive") -> dict[str, int | float]:
        now = time.monotonic()
        bucket_key = f"{bucket}:{key_id}"
        with self._lock:
            tokens, updated = self._buckets.get(bucket_key, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - updated) * self.refill_per_second)
            if tokens < weight:
                retry_after = math.ceil((weight - tokens) / self.refill_per_second) if self.refill_per_second else 60
                raise RateLimitError("rate limit exceeded", retry_after=max(1, retry_after))
            remaining = max(0.0, tokens - weight)
            self._buckets[bucket_key] = (remaining, now)
            reset = math.ceil((self.capacity - remaining) / self.refill_per_second) if self.refill_per_second else 0
            return {"limit": self.capacity, "remaining": remaining, "reset": int(time.time()) + max(0, reset)}
