"""Production relational-store boundary with optional PostgreSQL support.

SQLite remains the deterministic local store. PostgreSQL is loaded lazily so the
base package stays dependency-free; install the optional ``postgres`` extra in a
staging or production image.
"""

from __future__ import annotations

import contextlib
import json
import math
import os
import queue
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

from .errors import RateLimitError
from .redaction import redact_text
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
    last_error TEXT NULL,
    last_delivery_id VARCHAR(100) NULL,
    last_delivery_status VARCHAR(32) NULL,
    last_delivery_attempts INTEGER NOT NULL DEFAULT 0,
    last_delivery_error TEXT NULL,
    change_policy_json JSONB NULL
);
ALTER TABLE monitors ADD COLUMN IF NOT EXISTS last_delivery_id VARCHAR(100) NULL;
ALTER TABLE monitors ADD COLUMN IF NOT EXISTS last_delivery_status VARCHAR(32) NULL;
ALTER TABLE monitors ADD COLUMN IF NOT EXISTS last_delivery_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE monitors ADD COLUMN IF NOT EXISTS last_delivery_error TEXT NULL;
ALTER TABLE monitors ADD COLUMN IF NOT EXISTS change_policy_json JSONB NULL;
CREATE TABLE IF NOT EXISTS scheduler_jobs (
    id VARCHAR(100) PRIMARY KEY,
    org_id VARCHAR(100) NOT NULL REFERENCES organizations(id),
    job_type VARCHAR(64) NOT NULL,
    monitor_id VARCHAR(100) NULL REFERENCES monitors(id),
    priority INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL,
    run_at TIMESTAMPTZ NOT NULL,
    lease_until TIMESTAMPTZ NULL,
    lease_token VARCHAR(100) NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    last_error TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_type, org_id, monitor_id)
);
ALTER TABLE scheduler_jobs ADD COLUMN IF NOT EXISTS lease_token VARCHAR(100) NULL;
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    job_id VARCHAR(100) PRIMARY KEY REFERENCES scheduler_jobs(id),
    org_id VARCHAR(100) NOT NULL REFERENCES organizations(id),
    monitor_id VARCHAR(100) NOT NULL REFERENCES monitors(id),
    url TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    last_status_code INTEGER NULL,
    last_error TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMPTZ NULL
);
CREATE TABLE IF NOT EXISTS webhook_delivery_attempts (
    id BIGSERIAL PRIMARY KEY,
    job_id VARCHAR(100) NOT NULL REFERENCES webhook_deliveries(job_id),
    org_id VARCHAR(100) NOT NULL REFERENCES organizations(id),
    attempt INTEGER NOT NULL,
    delivered BOOLEAN NOT NULL,
    status_code INTEGER NULL,
    error TEXT NULL,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_org_status ON webhook_deliveries(org_id, status, updated_at);
CREATE INDEX IF NOT EXISTS idx_webhook_attempts_job ON webhook_delivery_attempts(job_id, attempted_at);
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
CREATE TABLE IF NOT EXISTS queue_rate_limits (
    org_id VARCHAR(100) NOT NULL REFERENCES organizations(id),
    bucket VARCHAR(64) NOT NULL,
    tokens DOUBLE PRECISION NOT NULL,
    capacity DOUBLE PRECISION NOT NULL,
    refill_per_second DOUBLE PRECISION NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (org_id, bucket)
);
CREATE INDEX IF NOT EXISTS idx_queue_rate_limits_updated ON queue_rate_limits(updated_at);
CREATE TABLE IF NOT EXISTS metric_points (
    org_id VARCHAR(100) NOT NULL REFERENCES organizations(id),
    metric_key TEXT NOT NULL,
    kind VARCHAR(32) NOT NULL,
    counter BIGINT NOT NULL DEFAULT 0,
    sample_count BIGINT NOT NULL DEFAULT 0,
    sample_sum DOUBLE PRECISION NOT NULL DEFAULT 0,
    gauge_value DOUBLE PRECISION NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (org_id, metric_key, kind)
);
CREATE INDEX IF NOT EXISTS idx_metric_points_org_time ON metric_points(org_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_metric_points_key ON metric_points(metric_key, kind);
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


class PostgresDistributedQueue(PostgresRelationalStore):
    """PostgreSQL coordination backend for multi-instance scheduler workers.

    Business records may remain on the local adapter during migration, but queue
    ownership and limiter state are coordinated transactionally in PostgreSQL.
    """

    @staticmethod
    def _timestamp(value: float | None) -> datetime:
        return datetime.fromtimestamp(time.time() if value is None else value, tz=timezone.utc)

    @staticmethod
    def _epoch(value: Any) -> float:
        if isinstance(value, datetime):
            return value.timestamp()
        return float(value)

    @staticmethod
    def _row_dict(cursor: Any, row: Any) -> dict[str, Any] | None:
        if not row:
            return None
        return dict(zip([item.name for item in cursor.description], row))

    def claim_due_job(self, now: float | None = None, lease_seconds: float = 120.0, org_id: str | None = None) -> dict[str, Any] | None:
        current = self._timestamp(now)
        token = "lease_" + uuid.uuid4().hex
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE scheduler_jobs SET status='pending', lease_until=NULL, lease_token=NULL, updated_at=%s "
                    "WHERE status='leased' AND lease_until IS NOT NULL AND lease_until < %s",
                    (current, current),
                )
                query = (
                    "SELECT * FROM scheduler_jobs WHERE status='pending' AND run_at <= %s"
                )
                params: list[Any] = [current]
                if org_id is not None:
                    query += " AND org_id=%s"
                    params.append(org_id)
                query += " ORDER BY priority DESC, run_at ASC, id ASC LIMIT 1 FOR UPDATE SKIP LOCKED"
                cursor.execute(query, tuple(params))
                row = cursor.fetchone()
                if not row:
                    return None
                selected = self._row_dict(cursor, row) or {}
                lease_until = current.timestamp() + max(1.0, float(lease_seconds))
                lease_until_dt = self._timestamp(lease_until)
                cursor.execute(
                    "UPDATE scheduler_jobs SET status='leased', lease_until=%s, lease_token=%s, attempts=attempts+1, updated_at=%s "
                    "WHERE id=%s AND status='pending'",
                    (lease_until_dt, token, current, selected["id"]),
                )
                selected.update(status="leased", lease_until=lease_until_dt, lease_token=token, attempts=int(selected.get("attempts", 0)) + 1)
                return selected

    def acknowledge_job(self, job_id: str, frequency: str, now: float | None = None, org_id: str | None = None, lease_token: str | None = None) -> bool:
        if not lease_token:
            return False
        current = self._timestamp(now)
        interval = {"minutely": 60, "hourly": 3600, "daily": 86400}.get(frequency, 3600)
        priority = {"minutely": 30, "hourly": 20, "daily": 10}.get(frequency, 10)
        query = "UPDATE scheduler_jobs SET status='pending', run_at=%s, lease_until=NULL, lease_token=NULL, attempts=0, last_error=NULL, priority=%s, updated_at=%s WHERE id=%s AND status='leased' AND lease_token=%s"
        params: list[Any] = [self._timestamp(current.timestamp() + interval), priority, current, job_id, lease_token]
        if org_id is not None:
            query += " AND org_id=%s"
            params.append(org_id)
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, tuple(params))
                return cursor.rowcount > 0

    def fail_job(self, job_id: str, error: str, now: float | None = None, org_id: str | None = None, retry_delay: float | None = None, lease_token: str | None = None) -> str:
        if not lease_token:
            return "missing"
        current = self._timestamp(now)
        message = redact_text(error)[:500]
        with self.connection() as connection:
            with connection.cursor() as cursor:
                query = "SELECT attempts, max_attempts FROM scheduler_jobs WHERE id=%s AND status='leased' AND lease_token=%s"
                params: list[Any] = [job_id, lease_token]
                if org_id is not None:
                    query += " AND org_id=%s"
                    params.append(org_id)
                cursor.execute(query, tuple(params))
                row = cursor.fetchone()
                if not row:
                    return "missing"
                attempts, max_attempts = int(row[0]), int(row[1])
                status = "dead_letter" if attempts >= max_attempts else "pending"
                delay = 0.5 * (2 ** max(0, attempts - 1)) if retry_delay is None else max(0.0, float(retry_delay))
                run_at = current if status == "dead_letter" else self._timestamp(current.timestamp() + min(delay, 30.0) if retry_delay is None else current.timestamp() + delay)
                update = "UPDATE scheduler_jobs SET status=%s, run_at=%s, lease_until=NULL, lease_token=NULL, last_error=%s, updated_at=%s WHERE id=%s AND status='leased' AND lease_token=%s"
                values: list[Any] = [status, run_at, message, current, job_id, lease_token]
                if org_id is not None:
                    update += " AND org_id=%s"
                    values.append(org_id)
                cursor.execute(update, tuple(values))
                return status if cursor.rowcount else "missing"

    def cancel_job(self, job_id: str, org_id: str | None = None, lease_token: str | None = None) -> bool:
        query = "UPDATE scheduler_jobs SET status='cancelled', lease_until=NULL, lease_token=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=%s"
        params: list[Any] = [job_id]
        if org_id is not None:
            query += " AND org_id=%s"
            params.append(org_id)
        if lease_token is not None:
            query += " AND lease_token=%s"
            params.append(lease_token)
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, tuple(params))
                return cursor.rowcount > 0

    def consume_rate_limit(self, org_id: str, bucket: str, cost: float, capacity: float, refill_per_second: float, now: float | None = None) -> dict[str, float]:
        if cost <= 0 or capacity <= 0 or refill_per_second < 0:
            raise ValueError("rate-limit parameters are invalid")
        current = self._timestamp(now)
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO queue_rate_limits(org_id, bucket, tokens, capacity, refill_per_second, updated_at) VALUES(%s, %s, %s, %s, %s, %s) ON CONFLICT (org_id, bucket) DO NOTHING",
                    (org_id, bucket, capacity, capacity, refill_per_second, current),
                )
                cursor.execute("SELECT tokens, capacity, refill_per_second, updated_at FROM queue_rate_limits WHERE org_id=%s AND bucket=%s FOR UPDATE", (org_id, bucket))
                row = cursor.fetchone()
                if not row:
                    raise RuntimeError("distributed rate-limit bucket was not created")
                tokens, stored_capacity, refill, updated_at = float(row[0]), float(row[1]), float(row[2]), row[3]
                elapsed = max(0.0, current.timestamp() - self._epoch(updated_at))
                available = min(stored_capacity, tokens + elapsed * refill)
                if available < cost:
                    cursor.execute("UPDATE queue_rate_limits SET tokens=%s, updated_at=%s WHERE org_id=%s AND bucket=%s", (available, current, org_id, bucket))
                    retry_after = math.ceil((cost - available) / refill) if refill > 0 else 3600
                    raise RateLimitError("distributed queue rate limit exceeded", retry_after=max(1, retry_after))
                remaining = available - cost
                cursor.execute("UPDATE queue_rate_limits SET tokens=%s, updated_at=%s WHERE org_id=%s AND bucket=%s", (remaining, current, org_id, bucket))
                return {"remaining": remaining, "reset": current.timestamp() + ((stored_capacity - remaining) / refill if refill > 0 else 0.0)}

    def queue_summary(self, org_id: str) -> dict[str, int]:
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT status, COUNT(*) FROM scheduler_jobs WHERE org_id=%s GROUP BY status", (org_id,))
                rows = cursor.fetchall()
                cursor.execute("SELECT COUNT(*) FROM scheduler_jobs WHERE org_id=%s AND status='pending' AND run_at <= CURRENT_TIMESTAMP", (org_id,))
                due = cursor.fetchone()[0]
        summary = {str(row[0]): int(row[1]) for row in rows}
        summary["due"] = int(due)
        return summary

    def sync_monitor(self, record: Any) -> None:
        org_id = str(record.org_id)
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO organizations(id, name) VALUES(%s, %s) ON CONFLICT (id) DO NOTHING", (org_id, org_id))
                cursor.execute(
                    "INSERT INTO monitors(id, org_id, task, status, frequency, target_url, webhook_url, last_checked_at, last_change_at, last_event, last_error, change_policy_json) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb) ON CONFLICT (id) DO UPDATE SET status=EXCLUDED.status, frequency=EXCLUDED.frequency, target_url=EXCLUDED.target_url, webhook_url=EXCLUDED.webhook_url, change_policy_json=EXCLUDED.change_policy_json",
                    (record.id, org_id, record.task, record.status, record.frequency, record.target_url, record.webhook_url, record.last_checked_at, record.last_change_at, record.last_event, record.last_error, json.dumps(record.change_policy) if record.change_policy else None),
                )

    def enqueue_monitor_job(self, job_id: str, org_id: str, monitor_id: str, frequency: str, run_at: float | None = None) -> None:
        current = self._timestamp(run_at)
        priority = {"minutely": 30, "hourly": 20, "daily": 10}.get(frequency, 10)
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO scheduler_jobs(id, org_id, job_type, monitor_id, priority, status, run_at, attempts, max_attempts, created_at, updated_at) VALUES(%s, %s, 'monitor_check', %s, %s, 'pending', %s, 0, 5, %s, %s) ON CONFLICT (id) DO NOTHING",
                    (job_id, org_id, monitor_id, priority, current, current, current),
                )

    def enqueue_webhook_delivery(self, job_id: str, org_id: str, monitor_id: str, url: str, payload: dict[str, Any], max_attempts: int = 5, run_at: float | None = None) -> None:
        current = self._timestamp(run_at)
        attempts = max(1, min(int(max_attempts), 5))
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO scheduler_jobs(id, org_id, job_type, monitor_id, priority, status, run_at, attempts, max_attempts, created_at, updated_at) VALUES(%s, %s, 'webhook_delivery', NULL, 5, 'pending', %s, 0, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                    (job_id, org_id, current, attempts, current, current),
                )
                cursor.execute(
                    "INSERT INTO webhook_deliveries(job_id, org_id, monitor_id, url, payload_json, status, attempts, max_attempts, created_at, updated_at) VALUES(%s, %s, %s, %s, %s::jsonb, 'pending', 0, %s, %s, %s) ON CONFLICT (job_id) DO NOTHING",
                    (job_id, org_id, monitor_id, url, json.dumps(payload, separators=(",", ":"), ensure_ascii=False), attempts, current, current),
                )


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


def open_distributed_queue(config: DatabaseConfig | None = None) -> PostgresDistributedQueue | None:
    """Open the optional PostgreSQL queue coordinator when explicitly enabled."""
    config = config or DatabaseConfig.from_environment()
    if os.getenv("AGENTWEB_DISTRIBUTED_QUEUE", "0").strip().lower() not in {"1", "true", "yes"}:
        return None
    if config.driver != "postgres":
        raise DatabaseConfigurationError("distributed queue mode requires a PostgreSQL DATABASE_URL")
    coordinator = PostgresDistributedQueue(config.url, config.pool_size)
    coordinator.bootstrap()
    return coordinator


def open_relational_store(config: DatabaseConfig | None = None):
    config = config or DatabaseConfig.from_environment()
    if config.driver == "postgres":
        return PostgresRelationalStore(config.url, config.pool_size)
    return SQLiteRelationalStore(config.sqlite_path)
