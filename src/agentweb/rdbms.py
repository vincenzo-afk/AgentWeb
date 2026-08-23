"""Production relational-store boundary with optional PostgreSQL support.

SQLite remains the deterministic local store. PostgreSQL is loaded lazily so the
base package stays dependency-free; install the optional ``postgres`` extra in a
staging or production image.
"""

from __future__ import annotations

import contextlib
import os
import queue
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

from .secrets import SecretProvider, SecretProviderError, build_provider


class DatabaseConfigurationError(RuntimeError):
    """Raised when production database configuration is unsafe or incomplete."""


POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(100) PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(100) PRIMARY KEY,
    org_id VARCHAR(100) NOT NULL REFERENCES organizations(id),
    scope JSONB NOT NULL,
    prefix VARCHAR(32) NOT NULL,
    hashed_secret TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMPTZ NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id VARCHAR(100) PRIMARY KEY,
    org_id VARCHAR(100) NOT NULL REFERENCES organizations(id),
    task TEXT NOT NULL,
    mode VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ NULL
);
CREATE TABLE IF NOT EXISTS monitors (
    id VARCHAR(100) PRIMARY KEY,
    org_id VARCHAR(100) NOT NULL REFERENCES organizations(id),
    task TEXT NOT NULL,
    status VARCHAR(32) NOT NULL,
    frequency VARCHAR(32) NOT NULL,
    target_url TEXT NULL,
    webhook_url TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_checked_at TIMESTAMPTZ NULL,
    last_change_at TIMESTAMPTZ NULL,
    last_event VARCHAR(64) NULL,
    last_error TEXT NULL
);
CREATE TABLE IF NOT EXISTS scheduler_jobs (
    id VARCHAR(100) PRIMARY KEY,
    org_id VARCHAR(100) NOT NULL REFERENCES organizations(id),
    job_type VARCHAR(64) NOT NULL,
    monitor_id VARCHAR(100) NULL REFERENCES monitors(id),
    priority INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL,
    run_at TIMESTAMPTZ NOT NULL,
    lease_until TIMESTAMPTZ NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    last_error TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_type, org_id, monitor_id)
);
CREATE TABLE IF NOT EXISTS audit_events (
    id VARCHAR(100) PRIMARY KEY,
    org_id VARCHAR(100) NOT NULL REFERENCES organizations(id),
    actor TEXT NOT NULL,
    action VARCHAR(128) NOT NULL,
    target TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS usage_records (
    id VARCHAR(100) PRIMARY KEY,
    org_id VARCHAR(100) NOT NULL REFERENCES organizations(id),
    period VARCHAR(32) NOT NULL,
    mode VARCHAR(32) NOT NULL,
    count BIGINT NOT NULL DEFAULT 0,
    cost NUMERIC(18, 6) NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_runs_org_created ON runs(org_id, created_at);
CREATE INDEX IF NOT EXISTS idx_monitors_org_status ON monitors(org_id, status);
CREATE INDEX IF NOT EXISTS idx_scheduler_org_due ON scheduler_jobs(org_id, status, run_at, priority);
CREATE INDEX IF NOT EXISTS idx_audit_org_time ON audit_events(org_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_usage_org_period ON usage_records(org_id, period);
CREATE INDEX IF NOT EXISTS idx_api_keys_org_revoked ON api_keys(org_id, revoked_at);
"""


@dataclass(frozen=True)
class DatabaseConfig:
    environment: str
    url: str
    pool_size: int = 4

    @classmethod
    def from_environment(cls, provider: SecretProvider | None = None) -> "DatabaseConfig":
        environment = os.getenv("AGENTWEB_ENV", "development").strip().lower()
        if environment not in {"development", "staging", "production"}:
            raise DatabaseConfigurationError("AGENTWEB_ENV must be development, staging, or production")
        provider = provider or build_provider()
        url = provider.get("DATABASE_URL", required=environment != "development")
        if not url:
            url = "sqlite:///agentweb.sqlite3"
        if environment != "development" and not url.startswith(("postgresql://", "postgres://")):
            raise DatabaseConfigurationError("staging and production require a PostgreSQL DATABASE_URL")
        try:
            pool_size = max(1, min(int(os.getenv("AGENTWEB_DB_POOL_SIZE", "4")), 32))
        except ValueError as error:
            raise DatabaseConfigurationError("AGENTWEB_DB_POOL_SIZE must be an integer") from error
        return cls(environment, url, pool_size)

    @property
    def driver(self) -> str:
        if self.url.startswith(("postgresql://", "postgres://")):
            return "postgres"
        if self.url.startswith("sqlite:///") or "://" not in self.url:
            return "sqlite"
        raise DatabaseConfigurationError("DATABASE_URL must use sqlite:/// or postgresql://")

    @property
    def sqlite_path(self) -> Path:
        if self.url.startswith("sqlite:///"):
            return Path(self.url[len("sqlite:///") :])
        return Path(self.url)


class PostgresRelationalStore:
    """Small bounded connection pool for the production relational schema."""

    def __init__(self, url: str, pool_size: int = 4) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
            raise DatabaseConfigurationError("invalid PostgreSQL DATABASE_URL")
        self.url = url
        self.pool_size = max(1, min(pool_size, 32))
        self._pool: queue.LifoQueue[Any] = queue.LifoQueue(maxsize=self.pool_size)
        self._created = 0
        self._lock = threading.Lock()
        self._closed = False

    def _driver(self):
        try:
            import psycopg  # type: ignore
        except ImportError as error:
            raise DatabaseConfigurationError("install agentweb[postgres] to use PostgreSQL") from error
        return psycopg

    def _new_connection(self):
        with self._lock:
            if self._closed:
                raise DatabaseConfigurationError("database pool is closed")
            if self._created >= self.pool_size:
                return None
            self._created += 1
        try:
            connection = self._driver().connect(self.url, connect_timeout=5)
            connection.autocommit = False
            return connection
        except Exception:
            with self._lock:
                self._created = max(0, self._created - 1)
            raise

    @contextlib.contextmanager
    def connection(self) -> Iterator[Any]:
        connection = None
        try:
            try:
                connection = self._pool.get_nowait()
            except queue.Empty:
                connection = self._new_connection()
                if connection is None:
                    connection = self._pool.get(timeout=10)
            yield connection
            connection.commit()
        except Exception:
            if connection is not None:
                connection.rollback()
            raise
        finally:
            if connection is not None and not self._closed:
                self._pool.put(connection)

    def bootstrap(self) -> None:
        with self.connection() as connection:
            with connection.cursor() as cursor:
                for statement in (part.strip() for part in POSTGRES_SCHEMA.split(";")):
                    if statement:
                        cursor.execute(statement)

    def health(self) -> bool:
        try:
            with self.connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return cursor.fetchone()[0] == 1
        except Exception:
            return False

    def get_monitor(self, monitor_id: str, org_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, org_id, task, status, frequency, target_url, webhook_url, created_at, last_checked_at, last_change_at, last_event, last_error "
                    "FROM monitors WHERE id=%s AND org_id=%s",
                    (monitor_id, org_id),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                columns = [item.name for item in cursor.description]
                return dict(zip(columns, row))

    def create_monitor(self, record: dict[str, Any]) -> None:
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO monitors(id, org_id, task, status, frequency, target_url, webhook_url, last_checked_at, last_change_at, last_event, last_error) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        record["id"], record["org_id"], record["task"], record["status"], record["frequency"],
                        record.get("target_url"), record.get("webhook_url"), record.get("last_checked_at"),
                        record.get("last_change_at"), record.get("last_event"), record.get("last_error"),
                    ),
                )

    def close(self) -> None:
        self._closed = True
        while True:
            try:
                connection = self._pool.get_nowait()
            except queue.Empty:
                break
            try:
                connection.close()
            finally:
                with self._lock:
                    self._created = max(0, self._created - 1)


class SQLiteRelationalStore:
    """Explicit adapter for local development and migration source databases."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row

    def health(self) -> bool:
        return self._connection.execute("SELECT 1").fetchone()[0] == 1

    def close(self) -> None:
        self._connection.close()


def open_relational_store(config: DatabaseConfig | None = None):
    config = config or DatabaseConfig.from_environment()
    if config.driver == "postgres":
        return PostgresRelationalStore(config.url, config.pool_size)
    return SQLiteRelationalStore(config.sqlite_path)
