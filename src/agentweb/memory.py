"""SQLite-backed immutable snapshots and monitor state with no external services."""

from __future__ import annotations

import difflib
import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from .models import Monitor


class MemoryStore:
    def __init__(self, path: str | Path = "agentweb.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
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
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(monitors)")}
            for name, definition in (
                ("webhook_url", "TEXT"),
                ("last_event", "TEXT"),
            ):
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
                """
                SELECT target, content_hash, content, captured_at
                FROM snapshots WHERE target = ? ORDER BY id DESC LIMIT 1
                """,
                (target,),
            ).fetchone()
        return dict(row) if row else None

    def get_snapshot(self, key: str) -> dict[str, str] | None:
        """Backward-compatible alias; keys now represent snapshot targets."""
        return self.get_latest(key)

    def list_snapshots(self, target: str) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT target, content_hash, content, captured_at
                FROM snapshots WHERE target = ? ORDER BY id ASC
                """,
                (target,),
            ).fetchall()
        return [dict(row) for row in rows]

    def snapshot(self, target: str, content: str, captured_at: str) -> dict[str, str]:
        """Store a new immutable content version and return its canonical record."""
        content_hash = self.content_hash(content)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO snapshots(target, content_hash, content, captured_at)
                VALUES(?, ?, ?, ?)
                """,
                (target, content_hash, content, captured_at),
            )
            row = connection.execute(
                """
                SELECT target, content_hash, content, captured_at
                FROM snapshots WHERE target = ? AND content_hash = ?
                """,
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
                """
                SELECT content_hash, content FROM snapshots
                WHERE target = ? AND content_hash IN (?, ?)
                """,
                (target, from_hash, to_hash),
            ).fetchall()
        contents = {row["content_hash"]: row["content"] for row in rows}
        if from_hash not in contents or to_hash not in contents:
            raise KeyError("snapshot hash not found for target")
        before = contents[from_hash].splitlines()
        after = contents[to_hash].splitlines()
        changes = list(difflib.unified_diff(before, after, lineterm=""))
        return {
            "target": target,
            "from_hash": from_hash,
            "to_hash": to_hash,
            "changed": bool(changes),
            "summary": "content changed" if changes else "no change",
            "changes": changes[:100],
        }

    def create_monitor(self, monitor: Monitor) -> None:
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

    def get_monitor(self, monitor_id: str) -> Monitor | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, task, status, frequency, target_url, webhook_url, last_checked_at,
                       last_change_at, last_event, last_error
                FROM monitors WHERE id = ?
                """,
                (monitor_id,),
            ).fetchone()
        return Monitor(**dict(row)) if row else None

    def update_monitor(self, monitor: Monitor) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE monitors SET status=?, frequency=?, target_url=?, webhook_url=?,
                last_checked_at=?, last_change_at=?, last_event=?, last_error=? WHERE id=?
                """,
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

    def delete_monitor(self, monitor_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM monitors WHERE id = ?", (monitor_id,))
        return cursor.rowcount > 0

    def export_debug(self) -> dict[str, Any]:
        with self._connect() as connection:
            monitors = [dict(row) for row in connection.execute("SELECT * FROM monitors")]
            snapshots = [
                dict(row)
                for row in connection.execute(
                    "SELECT target, content_hash, captured_at FROM snapshots ORDER BY id"
                )
            ]
        return {"monitors": monitors, "snapshots": snapshots}
