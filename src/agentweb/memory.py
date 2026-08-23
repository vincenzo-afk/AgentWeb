"""SQLite-backed immutable snapshots, monitor state, and durable scheduler jobs."""

from __future__ import annotations

import difflib
import hashlib
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
            legacy_snapshots = "key" in snapshot_columns and "target" not in snapshot_columns
            if legacy_snapshots:
                connection.execute("ALTER TABLE snapshots RENAME TO snapshots_legacy")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    content TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    UNIQUE(target, content_hash)
                );
                CREATE INDEX IF NOT EXISTS idx_snapshots_target_time
                    ON snapshots(target, captured_at);
                CREATE TABLE IF NOT EXISTS monitors (
                    id TEXT PRIMARY KEY,
                    task TEXT NOT NULL,
                    status TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    target_url TEXT,
                    webhook_url TEXT,
                    last_checked_at TEXT,
                    last_change_at TEXT,
                    last_event TEXT,
                    last_error TEXT
                );
                CREATE TABLE IF NOT EXISTS scheduler_jobs (
                    id TEXT PRIMARY KEY,
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
                    UNIQUE(job_type, monitor_id)
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_due
                    ON scheduler_jobs(status, run_at, priority);
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(monitors)")}
            for name, definition in (("webhook_url", "TEXT"), ("last_event", "TEXT")):
                if name not in columns:
                    connection.execute(f"ALTER TABLE monitors ADD COLUMN {name} {definition}")
            if legacy_snapshots:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO snapshots(target, content_hash, content, captured_at)
                    SELECT key, content_hash, content, captured_at FROM snapshots_legacy
                    """
                )
                connection.execute("DROP TABLE snapshots_legacy")

    @staticmethod
    def content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()

    def get_latest(self, target: str) -> dict[str, str] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT target, content_hash, content, captured_at FROM snapshots "
                "WHERE target = ? ORDER BY id DESC LIMIT 1",
                (target,),
            ).fetchone()
        return dict(row) if row else None

    def get_snapshot(self, key: str) -> dict[str, str] | None:
        """Backward-compatible alias; keys now represent snapshot targets."""
        return self.get_latest(key)

    def list_snapshots(self, target: str) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT target, content_hash, content, captured_at FROM snapshots "
                "WHERE target = ? ORDER BY id ASC",
                (target,),
            ).fetchall()
        return [dict(row) for row in rows]

    def snapshot(self, target: str, content: str, captured_at: str) -> dict[str, str]:
        """Store a new immutable content version and return its canonical record."""
        content_hash = self.content_hash(content)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO snapshots(target, content_hash, content, captured_at) VALUES(?, ?, ?, ?)",
                (target, content_hash, content, captured_at),
            )
            row = connection.execute(
                "SELECT target, content_hash, content, captured_at FROM snapshots "
                "WHERE target = ? AND content_hash = ?",
                (target, content_hash),
            ).fetchone()
        return dict(row)

    def save_snapshot(self, key: str, url: str, content: str, captured_at: str) -> bool:
        """Store content immutably and report whether it differs from the latest version."""
        previous = self.get_latest(key)
        self.snapshot(key, content, captured_at)
        return previous is not None and previous["content_hash"] != self.content_hash(content)

    def diff(self, target: str, from_hash: str, to_hash: str) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT content_hash, content FROM snapshots "
                "WHERE target = ? AND content_hash IN (?, ?)",
                (target, from_hash, to_hash),
            ).fetchall()
        contents = {row["content_hash"]: row["content"] for row in rows}
        if from_hash not in contents or to_hash not in contents:
            raise KeyError("snapshot hash not found for target")
        changes = list(
            difflib.unified_diff(contents[from_hash].splitlines(), contents[to_hash].splitlines(), lineterm="")
        )
        return {
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
                """
                INSERT INTO monitors(id, task, status, frequency, target_url, webhook_url,
                                     last_checked_at, last_change_at, last_event, last_error)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    monitor.id,
                    monitor.task,
                    monitor.status,
                    monitor.frequency,
                    monitor.target_url,
                    monitor.webhook_url,
                    monitor.last_checked_at,
                    monitor.last_change_at,
                    monitor.last_event,
                    monitor.last_error,
                ),
            )
            connection.execute(
                """
                INSERT INTO scheduler_jobs(id, job_type, monitor_id, priority, status, run_at,
                                           lease_until, attempts, max_attempts, last_error, created_at, updated_at)
                VALUES(?, 'monitor_check', ?, ?, 'pending', ?, NULL, 0, 5, NULL, ?, ?)
                """,
                (
                    "job_" + uuid.uuid4().hex[:16],
                    monitor.id,
                    self._frequency_priority(monitor.frequency),
                    now,
                    now,
                    now,
                ),
            )

    def get_monitor(self, monitor_id: str) -> Monitor | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, task, status, frequency, target_url, webhook_url, last_checked_at, "
                "last_change_at, last_event, last_error FROM monitors WHERE id = ?",
                (monitor_id,),
            ).fetchone()
        return Monitor(**dict(row)) if row else None

    def update_monitor(self, monitor: Monitor) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE monitors SET status=?, frequency=?, target_url=?, webhook_url=?, "
                "last_checked_at=?, last_change_at=?, last_event=?, last_error=? WHERE id=?",
                (
                    monitor.status,
                    monitor.frequency,
                    monitor.target_url,
                    monitor.webhook_url,
                    monitor.last_checked_at,
                    monitor.last_change_at,
                    monitor.last_event,
                    monitor.last_error,
                    monitor.id,
                ),
            )
            if monitor.status != "active":
                connection.execute(
                    "UPDATE scheduler_jobs SET status='cancelled', updated_at=? WHERE monitor_id=? "
                    "AND status IN ('pending', 'leased')",
                    (time.time(), monitor.id),
                )

    def delete_monitor(self, monitor_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM monitors WHERE id = ?", (monitor_id,))
            connection.execute("DELETE FROM scheduler_jobs WHERE monitor_id = ?", (monitor_id,))
        return cursor.rowcount > 0

    def claim_due_job(self, now: float | None = None, lease_seconds: float = 120.0) -> dict[str, Any] | None:
        now = time.time() if now is None else now
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE scheduler_jobs SET status='pending', lease_until=NULL, updated_at=? "
                "WHERE status='leased' AND lease_until IS NOT NULL AND lease_until < ?",
                (now, now),
            )
            row = connection.execute(
                "SELECT * FROM scheduler_jobs WHERE status='pending' AND run_at <= ? "
                "ORDER BY priority DESC, run_at ASC LIMIT 1",
                (now,),
            ).fetchone()
            if not row:
                connection.commit()
                return None
            lease_until = now + lease_seconds
            connection.execute(
                "UPDATE scheduler_jobs SET status='leased', lease_until=?, attempts=attempts+1, updated_at=? WHERE id=?",
                (lease_until, now, row["id"]),
            )
            claimed = dict(row)
            claimed["status"] = "leased"
            claimed["lease_until"] = lease_until
            claimed["attempts"] = int(row["attempts"]) + 1
            connection.commit()
        return claimed

    def acknowledge_job(self, job_id: str, frequency: str, now: float | None = None) -> None:
        now = time.time() if now is None else now
        next_run = now + self._frequency_seconds(frequency)
        with self._connect() as connection:
            connection.execute(
                "UPDATE scheduler_jobs SET status='pending', run_at=?, lease_until=NULL, attempts=0, "
                "last_error=NULL, priority=?, updated_at=? WHERE id=?",
                (next_run, self._frequency_priority(frequency), now, job_id),
            )

    def fail_job(self, job_id: str, error: str, now: float | None = None) -> str:
        now = time.time() if now is None else now
        with self._connect() as connection:
            row = connection.execute("SELECT attempts, max_attempts FROM scheduler_jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                return "missing"
            attempts = int(row["attempts"])
            if attempts >= int(row["max_attempts"]):
                status = "dead_letter"
                run_at = now
            else:
                status = "pending"
                run_at = now + min(0.5 * (2 ** max(0, attempts - 1)), 30.0)
            connection.execute(
                "UPDATE scheduler_jobs SET status=?, run_at=?, lease_until=NULL, last_error=?, updated_at=? WHERE id=?",
                (status, run_at, error[:500], now, job_id),
            )
        return status

    def cancel_job(self, job_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE scheduler_jobs SET status='cancelled', lease_until=NULL, updated_at=? WHERE id=?",
                (time.time(), job_id),
            )
        return cursor.rowcount > 0

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM scheduler_jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def list_jobs(self, status: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM scheduler_jobs"
        params: tuple[Any, ...] = ()
        if status:
            query += " WHERE status=?"
            params = (status,)
        query += " ORDER BY priority DESC, run_at ASC"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def export_debug(self) -> dict[str, Any]:
        with self._connect() as connection:
            monitors = [dict(row) for row in connection.execute("SELECT * FROM monitors")]
            snapshots = [
                dict(row)
                for row in connection.execute("SELECT target, content_hash, captured_at FROM snapshots ORDER BY id")
            ]
            jobs = [dict(row) for row in connection.execute("SELECT * FROM scheduler_jobs ORDER BY run_at")]
        return {"monitors": monitors, "snapshots": snapshots, "jobs": jobs}
