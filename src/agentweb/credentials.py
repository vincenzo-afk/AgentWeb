"""Encrypted, tenant-scoped credentials for rendered browser workflows."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from .errors import BrowserUnavailableError, InvalidRequestError
from .secrets import SecretProvider


class BrowserCredentialStore:
    """Persist browser credential secrets encrypted with a provider-backed Fernet key."""

    _KEY_NAME = "AGENTWEB_BROWSER_CREDENTIAL_KEY"

    def __init__(self, path: str | Path, secret_provider: SecretProvider) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.secret_provider = secret_provider
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS audit_events ("
                "id TEXT PRIMARY KEY, org_id TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT NOT NULL, "
                "timestamp REAL NOT NULL, metadata TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS browser_credentials ("
                "id TEXT PRIMARY KEY, org_id TEXT NOT NULL, label TEXT NOT NULL, username TEXT NOT NULL, "
                "encrypted_secret TEXT NOT NULL, created_at REAL NOT NULL, revoked_at REAL)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_browser_credentials_org ON browser_credentials(org_id, revoked_at)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _fernet(self):
        try:
            from cryptography.fernet import Fernet, InvalidToken
        except ImportError as error:
            raise BrowserUnavailableError("encrypted browser credentials require the browser security extra") from error
        raw_key = self.secret_provider.get(self._KEY_NAME, required=False)
        if not raw_key:
            raise BrowserUnavailableError("browser credential encryption is not configured")
        try:
            return Fernet(raw_key.encode("ascii")), InvalidToken
        except (ValueError, UnicodeEncodeError) as error:
            raise BrowserUnavailableError("browser credential encryption key is invalid") from error

    @staticmethod
    def _text(value: Any, field: str, maximum: int, *, trim: bool = True) -> str:
        if not isinstance(value, str):
            raise InvalidRequestError(f"{field} must be a string")
        if trim:
            value = value.strip()
        if not value or len(value) > maximum:
            raise InvalidRequestError(f"{field} must contain between 1 and {maximum} characters")
        return value

    def create(self, org_id: str, label: Any, username: Any, secret: Any, actor: str) -> dict[str, Any]:
        label = self._text(label, "label", 100)
        username = self._text(username, "username", 320)
        secret = self._text(secret, "secret", 10_000, trim=False)
        fernet, _ = self._fernet()
        credential_id = "cred_" + uuid.uuid4().hex[:16]
        created_at = time.time()
        encrypted = fernet.encrypt(secret.encode("utf-8")).decode("ascii")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO browser_credentials(id, org_id, label, username, encrypted_secret, created_at, revoked_at) "
                "VALUES (?, ?, ?, ?, ?, ?, NULL)",
                (credential_id, org_id, label, username, encrypted, created_at),
            )
        self._audit(org_id, actor, "browser_credential.created", credential_id, {"label": label})
        return {"id": credential_id, "org_id": org_id, "label": label, "username": username, "created_at": created_at, "revoked_at": None}

    def list(self, org_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, org_id, label, username, created_at, revoked_at FROM browser_credentials "
                "WHERE org_id=? ORDER BY created_at DESC, id DESC",
                (org_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def resolve(self, org_id: str, credential_id: Any) -> dict[str, str] | None:
        credential_id = self._text(credential_id, "credential_id", 100)
        fernet, invalid_token = self._fernet()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT username, encrypted_secret FROM browser_credentials "
                "WHERE id=? AND org_id=? AND revoked_at IS NULL",
                (credential_id, org_id),
            ).fetchone()
        if row is None:
            return None
        try:
            secret = fernet.decrypt(row["encrypted_secret"].encode("ascii")).decode("utf-8")
        except (invalid_token, UnicodeDecodeError, ValueError) as error:
            raise BrowserUnavailableError("browser credential could not be decrypted") from error
        return {"username": row["username"], "secret": secret}

    def revoke(self, org_id: str, credential_id: str, actor: str) -> bool:
        credential_id = self._text(credential_id, "credential_id", 100)
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE browser_credentials SET revoked_at=? WHERE id=? AND org_id=? AND revoked_at IS NULL",
                (time.time(), credential_id, org_id),
            )
        if cursor.rowcount:
            self._audit(org_id, actor, "browser_credential.revoked", credential_id, {})
            return True
        return False

    def _audit(self, org_id: str, actor: str, action: str, target: str, metadata: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO audit_events(id, org_id, actor, action, target, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("aud_" + uuid.uuid4().hex[:16], org_id, actor[:100], action[:100], target[:200], time.time(), json.dumps(metadata, separators=(",", ":"))),
            )
