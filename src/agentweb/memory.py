"""SQLite-backed snapshots with no external services or dependencies."""

from __future__ import annotations

import hashlib
import json
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
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    key TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    content TEXT NOT NULL,
                    captured_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS monitors (
                    id TEXT PRIMARY KEY,
                    task TEXT NOT NULL,
                    status TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    target_url TEXT,
                    last_checked_at TEXT,
                    last_change_at TEXT,
                    last_error TEXT
                );
                """
            )

    @staticmethod
    def content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()

    def get_snapshot(self, key: str) -> dict[str, str] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT url, content_hash, content, captured_at FROM snapshots WHERE key = ?",
                (key,),
            ).fetchone()
        return dict(row) if row else None

    def save_snapshot(self, key: str, url: str, content: str, captured_at: str) -> bool:
        current_hash = self.content_hash(content)
        previous = self.get_snapshot(key)
        changed = previous is not None and previous["content_hash"] != current_hash
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO snapshots(key, url, content_hash, content, captured_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    url=excluded.url,
                    content_hash=excluded.content_hash,
                    content=excluded.content,
                    captured_at=excluded.captured_at
                """,
                (key, url, current_hash, content, captured_at),
            )
        return changed

    def create_monitor(self, monitor: Monitor) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO monitors(id, task, status, frequency, target_url,
                                     last_checked_at, last_change_at, last_error)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    monitor.id,
                    monitor.task,
                    monitor.status,
                    monitor.frequency,
                    monitor.target_url,
                    monitor.last_checked_at,
                    monitor.last_change_at,
                    monitor.last_error,
                ),
            )

    def get_monitor(self, monitor_id: str) -> Monitor | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, task, status, frequency, target_url, last_checked_at,
                       last_change_at, last_error
                FROM monitors WHERE id = ?
                """,
                (monitor_id,),
            ).fetchone()
        return Monitor(**dict(row)) if row else None

    def update_monitor(self, monitor: Monitor) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE monitors SET status=?, frequency=?, target_url=?, last_checked_at=?,
                last_change_at=?, last_error=? WHERE id=?
                """,
                (
                    monitor.status,
                    monitor.frequency,
                    monitor.target_url,
                    monitor.last_checked_at,
                    monitor.last_change_at,
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
                    "SELECT key, url, content_hash, captured_at FROM snapshots"
                )
            ]
        return {"monitors": monitors, "snapshots": snapshots}
