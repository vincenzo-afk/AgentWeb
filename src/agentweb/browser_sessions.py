from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken

from .errors import BrowserUnavailableError
from .redaction import redact_url


class BrowserSessionStore:
    """Persist encrypted browser storage state without exposing session tokens."""

    _max_state_bytes = 2_000_000

    def __init__(self, path: str | Path, secret_provider: Any) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.secret_provider = secret_provider
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS browser_session_states (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    encrypted_state TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_used_at REAL,
                    revoked_at REAL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_browser_session_states_org ON browser_session_states(org_id, revoked_at, created_at)"
            )

    def _fernet(self) -> Fernet:
        try:
            key = self.secret_provider.get("AGENTWEB_BROWSER_CREDENTIAL_KEY", required=True)
        except Exception as error:
            raise BrowserUnavailableError("browser session-state key is not configured") from error
        try:
            return Fernet(key.encode("ascii") if isinstance(key, str) else key)
        except (TypeError, ValueError) as error:
            raise BrowserUnavailableError("browser session-state key is invalid") from error

    @staticmethod
    def _text(value: object, name: str, maximum: int = 200) -> str:
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
            raise ValueError(f"{name} must be a non-empty string up to {maximum} characters")
        return value.strip()

    @staticmethod
    def _origin(url_or_origin: str) -> str:
        parsed = urlparse(url_or_origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("session state origin must be an absolute HTTP(S) origin")
        if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
            raise ValueError("session state origin cannot contain credentials")
        return f"{parsed.scheme}://{parsed.netloc.lower()}"

    @classmethod
    def _encode_state(cls, state: object, origin: str) -> str:
        if not isinstance(state, dict):
            raise ValueError("browser storage state must be an object")
        if set(state) - {"cookies", "origins"}:
            raise ValueError("browser storage state may contain only cookies and origins")
        cookies = state.get("cookies", [])
        origins = state.get("origins", [])
        if not isinstance(cookies, list) or not isinstance(origins, list) or len(cookies) > 200 or len(origins) > 50:
            raise ValueError("browser storage state contains too many cookies or origins")
        host = urlparse(origin).hostname or ""
        for cookie in cookies:
            if not isinstance(cookie, dict) or not isinstance(cookie.get("name"), str) or not isinstance(cookie.get("value"), str):
                raise ValueError("browser cookies must contain string name and value")
            if len(cookie["name"]) > 200 or len(cookie["value"]) > 10000:
                raise ValueError("browser cookie fields are too large")
            if cookie.get("url") and cls._origin(cookie["url"]) != origin:
                raise ValueError("browser cookie URL must match the session-state origin")
            domain = str(cookie.get("domain", "")).lstrip(".").lower()
            if domain and not (host == domain or host.endswith("." + domain)):
                raise ValueError("browser cookie domain must match the session-state origin")
        for entry in origins:
            if not isinstance(entry, dict) or cls._origin(entry.get("origin", "")) != origin:
                raise ValueError("browser storage origin must match the session-state origin")
            local_storage = entry.get("localStorage", [])
            if not isinstance(local_storage, list) or len(local_storage) > 500:
                raise ValueError("browser local storage is too large")
            for item in local_storage:
                if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("value"), str):
                    raise ValueError("browser local storage entries must contain string name and value")
                if len(item["name"]) > 200 or len(item["value"]) > 10000:
                    raise ValueError("browser local storage fields are too large")
        try:
            encoded = json.dumps(state, separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError) as error:
            raise ValueError("browser storage state must be JSON serializable") from error
        if len(encoded.encode("utf-8")) > cls._max_state_bytes:
            raise ValueError("browser storage state is too large")
        return encoded

    @staticmethod
    def _metadata(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "org_id": row["org_id"],
            "label": row["label"],
            "origin": row["origin"],
            "created_at": row["created_at"],
            "last_used_at": row["last_used_at"],
            "revoked_at": row["revoked_at"],
        }

    def create(self, org_id: str, label: str, origin: str, state: dict[str, Any], actor: str = "system") -> dict[str, Any]:
        label = self._text(label, "label", 100)
        origin = self._origin(origin)
        encoded = self._encode_state(state, origin)
        now = time.time()
        state_id = "bstate_" + uuid.uuid4().hex[:16]
        encrypted = self._fernet().encrypt(encoded.encode("utf-8")).decode("ascii")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO browser_session_states(id, org_id, label, origin, encrypted_state, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (state_id, org_id, label, origin, encrypted, now),
            )
        self._audit(org_id, actor, "browser_session_state.created", state_id, {"origin": redact_url(origin)})
        return {"id": state_id, "org_id": org_id, "label": label, "origin": origin, "created_at": now, "last_used_at": None, "revoked_at": None}

    def update(self, org_id: str, state_id: str, origin: str, state: dict[str, Any], actor: str = "system") -> dict[str, Any] | None:
        state_id = self._text(state_id, "session_state_id", 100)
        origin = self._origin(origin)
        encoded = self._encode_state(state, origin)
        encrypted = self._fernet().encrypt(encoded.encode("utf-8")).decode("ascii")
        now = time.time()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, org_id, label, origin, created_at, last_used_at, revoked_at FROM browser_session_states WHERE id=? AND org_id=? AND revoked_at IS NULL",
                (state_id, org_id),
            ).fetchone()
            if not row or row["origin"] != origin:
                return None
            connection.execute("UPDATE browser_session_states SET encrypted_state=?, last_used_at=? WHERE id=? AND org_id=? AND revoked_at IS NULL", (encrypted, now, state_id, org_id))
        self._audit(org_id, actor, "browser_session_state.updated", state_id, {})
        metadata = dict(self._metadata(row))
        metadata["last_used_at"] = now
        return metadata

    def resolve(self, org_id: str, state_id: str, origin: str) -> dict[str, Any] | None:
        state_id = self._text(state_id, "session_state_id", 100)
        origin = self._origin(origin)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, org_id, label, origin, encrypted_state, created_at, last_used_at, revoked_at FROM browser_session_states WHERE id=? AND org_id=? AND revoked_at IS NULL",
                (state_id, org_id),
            ).fetchone()
            if not row or row["origin"] != origin:
                return None
            connection.execute("UPDATE browser_session_states SET last_used_at=? WHERE id=? AND org_id=? AND revoked_at IS NULL", (time.time(), state_id, org_id))
        try:
            decoded = self._fernet().decrypt(row["encrypted_state"].encode("ascii"))
            state = json.loads(decoded.decode("utf-8"))
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as error:
            raise BrowserUnavailableError("browser session state could not be decrypted") from error
        if not isinstance(state, dict):
            raise BrowserUnavailableError("browser session state is invalid")
        return state

    def list(self, org_id: str, include_revoked: bool = False) -> list[dict[str, Any]]:
        clause = "" if include_revoked else " AND revoked_at IS NULL"
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, org_id, label, origin, created_at, last_used_at, revoked_at FROM browser_session_states WHERE org_id=?" + clause + " ORDER BY created_at DESC LIMIT 100",
                (org_id,),
            ).fetchall()
        return [self._metadata(row) for row in rows]

    def revoke(self, org_id: str, state_id: str, actor: str = "system") -> bool:
        state_id = self._text(state_id, "session_state_id", 100)
        with self._connect() as connection:
            changed = connection.execute("UPDATE browser_session_states SET revoked_at=? WHERE id=? AND org_id=? AND revoked_at IS NULL", (time.time(), state_id, org_id)).rowcount
        if changed:
            self._audit(org_id, actor, "browser_session_state.revoked", state_id, {})
        return bool(changed)

    def delete_all(self, org_id: str) -> int:
        with self._connect() as connection:
            return int(connection.execute("DELETE FROM browser_session_states WHERE org_id=?", (org_id,)).rowcount)

    def _audit(self, org_id: str, actor: str, action: str, target: str, metadata: dict[str, Any]) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO audit_events(id, org_id, actor, action, target, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("aud_" + uuid.uuid4().hex[:16], org_id, str(actor)[:100], action[:100], target[:200], time.time(), json.dumps(metadata, separators=(",", ":"))),
                )
        except sqlite3.Error:
            # Session-state writes must not fail because audit storage is unavailable;
            # the main security boundary remains encryption and tenant scoping.
            pass
