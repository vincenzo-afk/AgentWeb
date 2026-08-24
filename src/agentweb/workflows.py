"""Opt-in event-driven workflows triggered by meaningful monitor events."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any


class WorkflowStore:
    """Persist workflow definitions and run outcomes without storing raw page content."""

    EVENTS = {"monitor.change_detected", "monitor.no_change"}
    MODES = {"flash", "focus", "dive"}

    def __init__(self, path: str | Path, executor: Callable[[str, str, str], Any]) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.executor = executor
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
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    monitor_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    task_template TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_workflows_org_monitor
                    ON workflows(org_id, monitor_id, event, status);
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    org_id TEXT NOT NULL,
                    monitor_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    status TEXT NOT NULL,
                    execution_id TEXT,
                    error TEXT,
                    created_at REAL NOT NULL,
                    completed_at REAL
                );
                CREATE INDEX IF NOT EXISTS idx_workflow_runs_org_created
                    ON workflow_runs(org_id, created_at DESC);
                """
            )

    @staticmethod
    def _workflow(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "org_id": row["org_id"],
            "name": row["name"],
            "monitor_id": row["monitor_id"],
            "event": row["event"],
            "task_template": row["task_template"],
            "mode": row["mode"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _run(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "workflow_id": row["workflow_id"],
            "org_id": row["org_id"],
            "monitor_id": row["monitor_id"],
            "event": row["event"],
            "status": row["status"],
            "execution_id": row["execution_id"],
            "error": row["error"],
            "created_at": row["created_at"],
            "completed_at": row["completed_at"],
        }

    def create(
        self,
        name: str,
        monitor_id: str,
        task_template: str,
        event: str = "monitor.change_detected",
        mode: str = "focus",
        org_id: str = "development",
    ) -> dict[str, Any]:
        name = str(name or "").strip()
        monitor_id = str(monitor_id or "").strip()
        task_template = str(task_template or "").strip()
        event = str(event or "").strip()
        mode = str(mode or "focus").strip()
        if not name or len(name) > 120:
            raise ValueError("name must contain between 1 and 120 characters")
        if not monitor_id:
            raise ValueError("monitor_id must be a non-empty string")
        if not task_template or len(task_template) > 2000:
            raise ValueError("task_template must contain between 1 and 2000 characters")
        if event not in self.EVENTS:
            raise ValueError("event must be monitor.change_detected or monitor.no_change")
        if mode not in self.MODES:
            raise ValueError("mode must be flash, focus, or dive")
        now = time.time()
        workflow_id = "wf_" + uuid.uuid4().hex[:16]
        with self._connect() as connection:
            monitor = connection.execute(
                "SELECT 1 FROM monitors WHERE id=? AND org_id=?", (monitor_id, org_id)
            ).fetchone()
            if monitor is None:
                raise ValueError("monitor not found")
            connection.execute(
                "INSERT INTO workflows (id, org_id, name, monitor_id, event, task_template, mode, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)",
                (workflow_id, org_id, name, monitor_id, event, task_template, mode, now, now),
            )
            row = connection.execute("SELECT * FROM workflows WHERE id=? AND org_id=?", (workflow_id, org_id)).fetchone()
            if row is None:
                raise RuntimeError("workflow creation failed")
            return self._workflow(row)

    def list(self, org_id: str = "development") -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM workflows WHERE org_id=? ORDER BY created_at DESC, id", (org_id,)
            ).fetchall()
        return [self._workflow(row) for row in rows]

    def list_runs(self, org_id: str = "development", limit: int = 100) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(int(limit), 100))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM workflow_runs WHERE org_id=? ORDER BY created_at DESC, id LIMIT ?",
                (org_id, bounded_limit),
            ).fetchall()
        return [self._run(row) for row in rows]

    def trigger_for_monitor(
        self,
        monitor_id: str,
        org_id: str,
        event: str,
        values: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if event not in self.EVENTS:
            return []
        with self._connect() as connection:
            workflows = connection.execute(
                "SELECT * FROM workflows WHERE org_id=? AND monitor_id=? AND event=? AND status='active' ORDER BY id",
                (org_id, monitor_id, event),
            ).fetchall()
        runs: list[dict[str, Any]] = []
        for workflow in workflows:
            run_id = "wfrun_" + uuid.uuid4().hex[:16]
            started = time.time()
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO workflow_runs (id, workflow_id, org_id, monitor_id, event, status, created_at) VALUES (?, ?, ?, ?, ?, 'running', ?)",
                    (run_id, workflow["id"], org_id, monitor_id, event, started),
                )
            status = "succeeded"
            execution_id = None
            error = None
            try:
                task = workflow["task_template"].format_map({key: str(value) for key, value in values.items()})
                if not task.strip() or len(task) > 2000:
                    raise ValueError("rendered workflow task must contain between 1 and 2000 characters")
                result = self.executor(task, workflow["mode"], org_id)
                execution_id = getattr(result, "execution_id", None)
                if execution_id is None and isinstance(result, dict):
                    execution_id = result.get("execution_id")
            except Exception as exc:  # noqa: BLE001 - workflow failure is persisted, not raised into monitor checks
                status = "failed"
                error = str(exc)[:500]
            completed = time.time()
            with self._connect() as connection:
                connection.execute(
                    "UPDATE workflow_runs SET status=?, execution_id=?, error=?, completed_at=? WHERE id=? AND org_id=?",
                    (status, execution_id, error, completed, run_id, org_id),
                )
                row = connection.execute("SELECT * FROM workflow_runs WHERE id=? AND org_id=?", (run_id, org_id)).fetchone()
            if row is not None:
                runs.append(self._run(row))
        return runs

    def health(self) -> bool:
        try:
            with self._connect() as connection:
                return connection.execute("SELECT 1").fetchone()[0] == 1
        except (OSError, sqlite3.Error):
            return False
