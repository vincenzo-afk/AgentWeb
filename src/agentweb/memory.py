"""SQLite-backed immutable snapshots, tenant-scoped monitor state, and durable jobs."""

from __future__ import annotations

import difflib
import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from .models import Monitor


class MemoryStore:
    def __init__(self, path: str | Path = "agentweb.sqlite3") -> None:
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
            snapshot_columns = {row[1] for row in connection.execute("PRAGMA table_info(snapshots)")}
            legacy_snapshots = bool(snapshot_columns) and "org_id" not in snapshot_columns
            if legacy_snapshots:
                connection.execute("ALTER TABLE snapshots RENAME TO snapshots_legacy")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    content TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    UNIQUE(org_id, target, content_hash)
                );
                CREATE INDEX IF NOT EXISTS idx_snapshots_org_target_time
                    ON snapshots(org_id, target, captured_at);
                CREATE TABLE IF NOT EXISTS monitors (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL DEFAULT 'legacy',
                    task TEXT NOT NULL,
                    status TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    target_url TEXT,
                    webhook_url TEXT,
                    last_checked_at TEXT,
                    last_change_at TEXT,
                    last_event TEXT,
                    last_error TEXT,
                    last_delivery_id TEXT,
                    last_delivery_status TEXT,
                    last_delivery_attempts INTEGER NOT NULL DEFAULT 0,
                    last_delivery_error TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_monitors_org ON monitors(org_id, status);
                CREATE TABLE IF NOT EXISTS scheduler_jobs (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL DEFAULT 'legacy',
                    job_type TEXT NOT NULL,
                    monitor_id TEXT,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    run_at REAL NOT NULL,
                    lease_until REAL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 5,
                    last_error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    UNIQUE(job_type, org_id, monitor_id)
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_org_due
                    ON scheduler_jobs(org_id, status, run_at, priority);
                CREATE TABLE IF NOT EXISTS webhook_deliveries (
                    job_id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    monitor_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 5,
                    last_status_code INTEGER,
                    last_error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    delivered_at REAL
                );
                CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_org_status
                    ON webhook_deliveries(org_id, status, updated_at);
                CREATE TABLE IF NOT EXISTS webhook_delivery_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    org_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    delivered INTEGER NOT NULL,
                    status_code INTEGER,
                    error TEXT,
                    attempted_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_webhook_attempts_job
                    ON webhook_delivery_attempts(job_id, attempted_at);
                CREATE TABLE IF NOT EXISTS idempotency_records (
                    org_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_status INTEGER,
                    response_body TEXT,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    PRIMARY KEY(org_id, idempotency_key)
                );
                CREATE INDEX IF NOT EXISTS idx_idempotency_expiry
                    ON idempotency_records(expires_at);
                CREATE TABLE IF NOT EXISTS usage_records (
                    org_id TEXT NOT NULL,
                    period TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    cost REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY(org_id, period, mode)
                );
                CREATE INDEX IF NOT EXISTS idx_usage_org_period
                    ON usage_records(org_id, period);
                """
            )
            monitor_columns = {row[1] for row in connection.execute("PRAGMA table_info(monitors)")}
            if monitor_columns and "org_id" not in monitor_columns:
                connection.execute("ALTER TABLE monitors ADD COLUMN org_id TEXT NOT NULL DEFAULT 'legacy'")
            monitor_columns = {row[1] for row in connection.execute("PRAGMA table_info(monitors)")}
            for name, definition in (("webhook_url", "TEXT"), ("last_event", "TEXT"), ("last_delivery_id", "TEXT"), ("last_delivery_status", "TEXT"), ("last_delivery_attempts", "INTEGER NOT NULL DEFAULT 0"), ("last_delivery_error", "TEXT")):
                if name not in monitor_columns:
                    connection.execute(f"ALTER TABLE monitors ADD COLUMN {name} {definition}")
            job_columns = {row[1] for row in connection.execute("PRAGMA table_info(scheduler_jobs)")}
            if job_columns and "org_id" not in job_columns:
                connection.execute("ALTER TABLE scheduler_jobs ADD COLUMN org_id TEXT NOT NULL DEFAULT 'legacy'")
            if legacy_snapshots:
                legacy_columns = {row[1] for row in connection.execute("PRAGMA table_info(snapshots_legacy)")}
                target_column = "target" if "target" in legacy_columns else "key"
                connection.execute(
                    f"INSERT OR IGNORE INTO snapshots(org_id, target, content_hash, content, captured_at) "
                    f"SELECT 'legacy', {target_column}, content_hash, content, captured_at FROM snapshots_legacy"
                )
                connection.execute("DROP TABLE snapshots_legacy")

    @staticmethod
    def content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()

    def get_latest(self, target: str, org_id: str = "development") -> dict[str, str] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT org_id, target, content_hash, content, captured_at FROM snapshots "
                "WHERE org_id = ? AND target = ? ORDER BY id DESC LIMIT 1",
                (org_id, target),
            ).fetchone()
        return dict(row) if row else None

    def get_snapshot(self, key: str, org_id: str = "development") -> dict[str, str] | None:
        return self.get_latest(key, org_id)

    def claim_idempotency(self, org_id: str, idempotency_key: str, request_hash: str, ttl_seconds: int = 86400) -> dict[str, Any] | None:
        now = time.time()
        with self._connect() as connection:
            connection.execute("DELETE FROM idempotency_records WHERE expires_at <= ?", (now,))
            inserted = connection.execute(
                "INSERT OR IGNORE INTO idempotency_records(org_id, idempotency_key, request_hash, status, created_at, expires_at) "
                "VALUES (?, ?, ?, 'in_progress', ?, ?)",
                (org_id, idempotency_key, request_hash, now, now + ttl_seconds),
            ).rowcount
            if inserted:
                return None
            row = connection.execute(
                "SELECT org_id, idempotency_key, request_hash, status, response_status, response_body, created_at, expires_at "
                "FROM idempotency_records WHERE org_id = ? AND idempotency_key = ?",
                (org_id, idempotency_key),
            ).fetchone()
        return dict(row) if row else None

    def complete_idempotency(self, org_id: str, idempotency_key: str, request_hash: str, response_status: int, response_body: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE idempotency_records SET status='completed', response_status=?, response_body=? "
                "WHERE org_id=? AND idempotency_key=? AND request_hash=? AND status='in_progress'",
                (response_status, response_body, org_id, idempotency_key, request_hash),
            )

    def release_idempotency(self, org_id: str, idempotency_key: str, request_hash: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM idempotency_records WHERE org_id=? AND idempotency_key=? AND request_hash=? AND status='in_progress'",
                (org_id, idempotency_key, request_hash),
            )

    @staticmethod
    def _usage_cost(mode: str) -> float:
        return {"flash": 0.01, "focus": 0.05, "dive": 0.20, "monitor_checks": 0.01}.get(mode, 0.0)

    def record_usage(self, org_id: str, mode: str, count: int = 1, now: float | None = None) -> None:
        if count <= 0:
            return
        normalized = "monitor_checks" if mode in {"monitor", "monitor_checks"} else mode
        if normalized not in {"flash", "focus", "dive", "monitor_checks"}:
            raise ValueError("usage mode is not supported")
        period = time.strftime("%Y-%m", time.gmtime(time.time() if now is None else now))
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO usage_records(org_id, period, mode, count, cost) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(org_id, period, mode) DO UPDATE SET count=count+excluded.count, cost=cost+excluded.cost",
                (org_id, period, normalized, count, count * self._usage_cost(normalized)),
            )

    def usage_summary(self, org_id: str, period: str | None = None) -> dict[str, Any]:
        period = period or time.strftime("%Y-%m", time.gmtime())
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT mode, count, cost FROM usage_records WHERE org_id=? AND period=?",
                (org_id, period),
            ).fetchall()
        counts = {mode: 0 for mode in ("flash", "focus", "dive", "monitor_checks")}
        estimated_cost = 0.0
        for row in rows:
            if row["mode"] in counts:
                counts[row["mode"]] = int(row["count"])
                estimated_cost += float(row["cost"])
        return {"period": period, "requests_by_mode": counts, "estimated_cost": round(estimated_cost, 2)}

    def list_snapshots(self, target: str, org_id: str = "development") -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT org_id, target, content_hash, content, captured_at FROM snapshots "
                "WHERE org_id = ? AND target = ? ORDER BY id ASC",
                (org_id, target),
            ).fetchall()
        return [dict(row) for row in rows]

    def snapshot(self, target: str, content: str, captured_at: str, org_id: str = "development") -> dict[str, str]:
        content_hash = self.content_hash(content)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO snapshots(org_id, target, content_hash, content, captured_at) VALUES(?, ?, ?, ?, ?)",
                (org_id, target, content_hash, content, captured_at),
            )
            row = connection.execute(
                "SELECT org_id, target, content_hash, content, captured_at FROM snapshots "
                "WHERE org_id = ? AND target = ? AND content_hash = ?",
                (org_id, target, content_hash),
            ).fetchone()
        return dict(row)

    def save_snapshot(self, key: str, url: str, content: str, captured_at: str, org_id: str = "development") -> bool:
        previous = self.get_latest(key, org_id)
        self.snapshot(key, content, captured_at, org_id)
        return previous is not None and previous["content_hash"] != self.content_hash(content)

    def diff(self, target: str, from_hash: str, to_hash: str, org_id: str = "development") -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT content_hash, content FROM snapshots WHERE org_id = ? AND target = ? "
                "AND content_hash IN (?, ?)",
                (org_id, target, from_hash, to_hash),
            ).fetchall()
        contents = {row["content_hash"]: row["content"] for row in rows}
        if from_hash not in contents or to_hash not in contents:
            raise KeyError("snapshot hash not found for target")
        changes = list(difflib.unified_diff(contents[from_hash].splitlines(), contents[to_hash].splitlines(), lineterm=""))
        return {
            "org_id": org_id,
            "target": target,
            "from_hash": from_hash,
            "to_hash": to_hash,
            "changed": bool(changes),
            "summary": "content changed" if changes else "no change",
            "changes": changes[:100],
        }

    @staticmethod
    def _frequency_seconds(frequency: str) -> int:
        return {"minutely": 60, "hourly": 3600, "daily": 86400}.get(frequency, 3600)

    @staticmethod
    def _frequency_priority(frequency: str) -> int:
        return {"minutely": 30, "hourly": 20, "daily": 10}.get(frequency, 10)

    def create_monitor(self, monitor: Monitor) -> None:
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO monitors(id, org_id, task, status, frequency, target_url, webhook_url, "
                "last_checked_at, last_change_at, last_event, last_error) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (monitor.id, monitor.org_id, monitor.task, monitor.status, monitor.frequency, monitor.target_url,
                 monitor.webhook_url, monitor.last_checked_at, monitor.last_change_at, monitor.last_event, monitor.last_error),
            )
            connection.execute(
                "INSERT INTO scheduler_jobs(id, org_id, job_type, monitor_id, priority, status, run_at, lease_until, "
                "attempts, max_attempts, last_error, created_at, updated_at) VALUES(?, ?, 'monitor_check', ?, ?, 'pending', ?, NULL, 0, 5, NULL, ?, ?)",
                ("job_" + uuid.uuid4().hex[:16], monitor.org_id, monitor.id, self._frequency_priority(monitor.frequency), now, now, now),
            )

    def list_monitors(self, org_id: str = "development") -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, org_id, task, status, frequency, target_url, webhook_url, last_checked_at, last_change_at, last_event, last_error, "
                "last_delivery_id, last_delivery_status, last_delivery_attempts, last_delivery_error "
                "FROM monitors WHERE org_id=? ORDER BY id ASC",
                (org_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_monitor(self, monitor_id: str, org_id: str = "development") -> Monitor | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, task, status, frequency, target_url, webhook_url, last_checked_at, last_change_at, "
                "last_event, last_error, last_delivery_id, last_delivery_status, last_delivery_attempts, last_delivery_error, org_id "
                "FROM monitors WHERE id = ? AND org_id = ?",
                (monitor_id, org_id),
            ).fetchone()
        return Monitor(**dict(row)) if row else None

    def update_monitor(self, monitor: Monitor) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE monitors SET status=?, frequency=?, target_url=?, webhook_url=?, last_checked_at=?, "
                "last_change_at=?, last_event=?, last_error=?, last_delivery_id=?, last_delivery_status=?, "
                "last_delivery_attempts=?, last_delivery_error=? WHERE id=? AND org_id=?",
                (monitor.status, monitor.frequency, monitor.target_url, monitor.webhook_url, monitor.last_checked_at,
                 monitor.last_change_at, monitor.last_event, monitor.last_error, monitor.last_delivery_id,
                 monitor.last_delivery_status, monitor.last_delivery_attempts, monitor.last_delivery_error,
                 monitor.id, monitor.org_id),
            )
            if monitor.status != "active":
                connection.execute(
                    "UPDATE scheduler_jobs SET status='cancelled', updated_at=? WHERE monitor_id=? AND org_id=? "
                    "AND status IN ('pending', 'leased')",
                    (time.time(), monitor.id, monitor.org_id),
                )

    def enqueue_webhook_delivery(
        self,
        org_id: str,
        monitor_id: str,
        url: str,
        payload: dict[str, Any],
        max_attempts: int = 5,
        run_at: float | None = None,
    ) -> str:
        now = time.time() if run_at is None else run_at
        job_id = "job_" + uuid.uuid4().hex[:16]
        attempts = max(1, min(int(max_attempts), 5))
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO scheduler_jobs(id, org_id, job_type, monitor_id, priority, status, run_at, lease_until, "
                "attempts, max_attempts, last_error, created_at, updated_at) VALUES(?, ?, 'webhook_delivery', NULL, 5, 'pending', ?, NULL, 0, ?, NULL, ?, ?)",
                (job_id, org_id, run_at if run_at is not None else now, attempts, now, now),
            )
            connection.execute(
                "INSERT INTO webhook_deliveries(job_id, org_id, monitor_id, url, payload_json, status, attempts, max_attempts, created_at, updated_at) "
                "VALUES(?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?)",
                (job_id, org_id, monitor_id, url, json.dumps(payload, separators=(",", ":"), ensure_ascii=False), attempts, now, now),
            )
            connection.execute(
                "UPDATE monitors SET last_delivery_id=?, last_delivery_status='pending', last_delivery_attempts=0, last_delivery_error=NULL WHERE id=? AND org_id=?",
                (job_id, monitor_id, org_id),
            )
        return job_id

    def get_webhook_delivery(self, job_id: str, org_id: str | None = None) -> dict[str, Any] | None:
        query = "SELECT * FROM webhook_deliveries WHERE job_id=?"
        params: list[Any] = [job_id]
        if org_id is not None:
            query += " AND org_id=?"
            params.append(org_id)
        with self._connect() as connection:
            row = connection.execute(query, tuple(params)).fetchone()
            success = connection.execute(
                "SELECT 1 FROM webhook_delivery_attempts WHERE job_id=? AND org_id=? AND delivered=1 LIMIT 1",
                (job_id, org_id) if org_id is not None else (job_id, row["org_id"] if row else ""),
            ).fetchone()
        if not row:
            return None
        delivery = dict(row)
        delivery["payload"] = json.loads(delivery.pop("payload_json"))
        delivery["already_delivered"] = bool(success)
        return delivery

    def record_webhook_attempt(
        self,
        job_id: str,
        org_id: str,
        delivered: bool,
        status_code: int | None,
        error: str | None,
        attempted_at: float | None = None,
    ) -> int:
        attempted_at = time.time() if attempted_at is None else attempted_at
        with self._connect() as connection:
            row = connection.execute(
                "SELECT attempts FROM webhook_deliveries WHERE job_id=? AND org_id=?",
                (job_id, org_id),
            ).fetchone()
            if not row:
                raise ValueError("webhook delivery job not found")
            attempt = int(row["attempts"]) + 1
            connection.execute(
                "INSERT INTO webhook_delivery_attempts(job_id, org_id, attempt, delivered, status_code, error, attempted_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (job_id, org_id, attempt, int(delivered), status_code, (error or "")[:500] or None, attempted_at),
            )
            connection.execute(
                "UPDATE webhook_deliveries SET attempts=?, last_status_code=?, last_error=?, updated_at=? WHERE job_id=? AND org_id=?",
                (attempt, status_code, (error or "")[:500] or None, attempted_at, job_id, org_id),
            )
            connection.execute(
                "UPDATE monitors SET last_delivery_attempts=?, last_delivery_error=? WHERE last_delivery_id=? AND org_id=?",
                (attempt, (error or "")[:500] or None, job_id, org_id),
            )
        return attempt

    def mark_webhook_delivery(self, job_id: str, org_id: str, status: str, error: str | None = None, delivered_at: float | None = None) -> None:
        if status not in {"pending", "retrying", "delivered", "dead_letter", "rate_limited"}:
            raise ValueError("unsupported webhook delivery status")
        delivered_at = time.time() if delivered_at is None else delivered_at
        with self._connect() as connection:
            delivery = connection.execute(
                "SELECT monitor_id, attempts FROM webhook_deliveries WHERE job_id=? AND org_id=?",
                (job_id, org_id),
            ).fetchone()
            if not delivery:
                return
            connection.execute(
                "UPDATE webhook_deliveries SET status=?, last_error=?, updated_at=?, delivered_at=? WHERE job_id=? AND org_id=?",
                (status, (error or "")[:500] or None, delivered_at, delivered_at if status == "delivered" else None, job_id, org_id),
            )
            connection.execute(
                "UPDATE monitors SET last_delivery_status=?, last_delivery_error=? WHERE id=? AND org_id=?",
                (status, (error or "")[:500] or None, delivery["monitor_id"], org_id),
            )

    def delete_monitor(self, monitor_id: str, org_id: str = "development") -> bool:
        with self._connect() as connection:
            delivery_jobs = [row[0] for row in connection.execute(
                "SELECT job_id FROM webhook_deliveries WHERE monitor_id=? AND org_id=?", (monitor_id, org_id)
            ).fetchall()]
            if delivery_jobs:
                placeholders = ",".join("?" for _ in delivery_jobs)
                connection.execute(
                    f"DELETE FROM webhook_delivery_attempts WHERE org_id=? AND job_id IN ({placeholders})",
                    (org_id, *delivery_jobs),
                )
                connection.execute(
                    f"DELETE FROM webhook_deliveries WHERE org_id=? AND job_id IN ({placeholders})",
                    (org_id, *delivery_jobs),
                )
                connection.execute(
                    f"DELETE FROM scheduler_jobs WHERE org_id=? AND id IN ({placeholders})",
                    (org_id, *delivery_jobs),
                )
            cursor = connection.execute("DELETE FROM monitors WHERE id = ? AND org_id = ?", (monitor_id, org_id))
            connection.execute("DELETE FROM scheduler_jobs WHERE monitor_id = ? AND org_id = ?", (monitor_id, org_id))
        return cursor.rowcount > 0

    def claim_due_job(self, now: float | None = None, lease_seconds: float = 120.0, org_id: str | None = None) -> dict[str, Any] | None:
        now = time.time() if now is None else now
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE scheduler_jobs SET status='pending', lease_until=NULL, updated_at=? "
                "WHERE status='leased' AND lease_until IS NOT NULL AND lease_until < ?",
                (now, now),
            )
            query = "SELECT * FROM scheduler_jobs WHERE status='pending' AND run_at <= ?"
            params: list[Any] = [now]
            if org_id is not None:
                query += " AND org_id = ?"
                params.append(org_id)
            query += " ORDER BY priority DESC, run_at ASC LIMIT 1"
            row = connection.execute(query, tuple(params)).fetchone()
            if not row:
                connection.commit()
                return None
            lease_until = now + lease_seconds
            connection.execute("UPDATE scheduler_jobs SET status='leased', lease_until=?, attempts=attempts+1, updated_at=? WHERE id=?", (lease_until, now, row["id"]))
            claimed = dict(row)
            claimed.update(status="leased", lease_until=lease_until, attempts=int(row["attempts"]) + 1)
            connection.commit()
        return claimed

    def acknowledge_job(self, job_id: str, frequency: str, now: float | None = None, org_id: str | None = None) -> None:
        now = time.time() if now is None else now
        next_run = now + self._frequency_seconds(frequency)
        query = "UPDATE scheduler_jobs SET status='pending', run_at=?, lease_until=NULL, attempts=0, last_error=NULL, priority=?, updated_at=? WHERE id=?"
        params: list[Any] = [next_run, self._frequency_priority(frequency), now, job_id]
        if org_id is not None:
            query += " AND org_id=?"
            params.append(org_id)
        with self._connect() as connection:
            connection.execute(query, tuple(params))

    def fail_job(self, job_id: str, error: str, now: float | None = None, org_id: str | None = None) -> str:
        now = time.time() if now is None else now
        with self._connect() as connection:
            query = "SELECT attempts, max_attempts FROM scheduler_jobs WHERE id=?"
            params: list[Any] = [job_id]
            if org_id is not None:
                query += " AND org_id=?"
                params.append(org_id)
            row = connection.execute(query, tuple(params)).fetchone()
            if not row:
                return "missing"
            attempts = int(row["attempts"])
            status = "dead_letter" if attempts >= int(row["max_attempts"]) else "pending"
            run_at = now if status == "dead_letter" else now + min(0.5 * (2 ** max(0, attempts - 1)), 30.0)
            update = "UPDATE scheduler_jobs SET status=?, run_at=?, lease_until=NULL, last_error=?, updated_at=? WHERE id=?"
            update_params: list[Any] = [status, run_at, error[:500], now, job_id]
            if org_id is not None:
                update += " AND org_id=?"
                update_params.append(org_id)
            connection.execute(update, tuple(update_params))
        return status

    def cancel_job(self, job_id: str, org_id: str | None = None) -> bool:
        query = "UPDATE scheduler_jobs SET status='cancelled', lease_until=NULL, updated_at=? WHERE id=?"
        params: list[Any] = [time.time(), job_id]
        if org_id is not None:
            query += " AND org_id=?"
            params.append(org_id)
        with self._connect() as connection:
            cursor = connection.execute(query, tuple(params))
        return cursor.rowcount > 0

    def get_job(self, job_id: str, org_id: str | None = None) -> dict[str, Any] | None:
        query = "SELECT * FROM scheduler_jobs WHERE id=?"
        params: list[Any] = [job_id]
        if org_id is not None:
            query += " AND org_id=?"
            params.append(org_id)
        with self._connect() as connection:
            row = connection.execute(query, tuple(params)).fetchone()
        return dict(row) if row else None

    def list_jobs(self, status: str | None = None, org_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM scheduler_jobs WHERE 1=1"
        params: list[Any] = []
        if status:
            query += " AND status=?"
            params.append(status)
        if org_id is not None:
            query += " AND org_id=?"
            params.append(org_id)
        query += " ORDER BY priority DESC, run_at ASC"
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def export_debug(self, org_id: str | None = None) -> dict[str, Any]:
        with self._connect() as connection:
            clause = "" if org_id is None else " WHERE org_id=?"
            params = () if org_id is None else (org_id,)
            monitors = [dict(row) for row in connection.execute("SELECT * FROM monitors" + clause, params)]
            snapshots = [dict(row) for row in connection.execute("SELECT org_id, target, content_hash, captured_at FROM snapshots" + clause, params)]
            jobs = [dict(row) for row in connection.execute("SELECT * FROM scheduler_jobs" + clause, params)]
            deliveries = [dict(row) for row in connection.execute("SELECT job_id, org_id, monitor_id, url, status, attempts, max_attempts, last_status_code, last_error, created_at, updated_at, delivered_at FROM webhook_deliveries" + clause, params)]
            attempts = [dict(row) for row in connection.execute("SELECT id, job_id, org_id, attempt, delivered, status_code, error, attempted_at FROM webhook_delivery_attempts" + clause, params)]
        return {"monitors": monitors, "snapshots": snapshots, "jobs": jobs, "webhook_deliveries": deliveries, "webhook_attempts": attempts}
