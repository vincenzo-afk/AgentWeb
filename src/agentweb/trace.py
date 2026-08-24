"""Append-only, tenant-scoped, secret-safe execution trace records."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .redaction import redact_text


@dataclass
class Span:
    component: str
    operation: str
    start_time: float
    end_time: float
    status: str
    input_summary: str = ""
    output_summary: str = ""


class TraceStore:
    def __init__(self, path: str | Path = "agentweb.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(execution_traces)")}
            if columns and "org_id" not in columns:
                connection.execute("ALTER TABLE execution_traces RENAME TO execution_traces_legacy")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_traces (
                    execution_id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL DEFAULT 'legacy',
                    created_at REAL NOT NULL,
                    status TEXT NOT NULL,
                    spans TEXT NOT NULL
                )
                """
            )
            if columns and "org_id" not in columns:
                connection.execute(
                    "INSERT OR IGNORE INTO execution_traces(execution_id, org_id, created_at, status, spans) "
                    "SELECT execution_id, 'legacy', created_at, status, spans FROM execution_traces_legacy"
                )
                connection.execute("DROP TABLE execution_traces_legacy")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_traces_org_time ON execution_traces(org_id, created_at)")

    def start(self) -> str:
        return "exec_" + uuid.uuid4().hex[:16]

    def save(self, execution_id: str, spans: list[Span], status: str = "complete", org_id: str = "development") -> None:
        sanitized = []
        for span in spans:
            item = asdict(span)
            for key, value in item.items():
                if isinstance(value, str):
                    item[key] = redact_text(value)
            sanitized.append(item)
        payload = json.dumps(sanitized, separators=(",", ":"))
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO execution_traces(execution_id, org_id, created_at, status, spans) VALUES (?, ?, ?, ?, ?)",
                (execution_id, org_id, time.time(), status, payload),
            )

    def replay(self, execution_id: str, org_id: str = "development") -> dict | None:
        """Return a sanitized historical execution projection; never re-execute work."""
        trace = self.get(execution_id, org_id)
        if not trace:
            return None
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, str]] = []
        for sequence, span in enumerate(trace.get("spans", []), start=1):
            node_id = f"step_{sequence}"
            nodes.append(
                {
                    "id": node_id,
                    "sequence": sequence,
                    "component": redact_text(str(span.get("component", ""))),
                    "operation": redact_text(str(span.get("operation", ""))),
                    "status": redact_text(str(span.get("status", ""))),
                    "duration_ms": round(max(0.0, float(span.get("end_time", 0.0)) - float(span.get("start_time", 0.0))) * 1000, 2),
                    "input_summary": redact_text(str(span.get("input_summary", ""))),
                    "output_summary": redact_text(str(span.get("output_summary", ""))),
                }
            )
            if sequence > 1:
                edges.append({"from": f"step_{sequence - 1}", "to": node_id})
        return {
            "execution_id": trace["execution_id"],
            "created_at": trace["created_at"],
            "status": trace["status"],
            "replayable": True,
            "historical": True,
            "network_reexecuted": False,
            "side_effects": False,
            "nodes": nodes,
            "edges": edges,
        }

    def delete(self, org_id: str, execution_id: str | None = None) -> int:
        query = "DELETE FROM execution_traces WHERE org_id=?"
        params: list[Any] = [org_id]
        if execution_id is not None:
            query += " AND execution_id=?"
            params.append(execution_id)
        with sqlite3.connect(self.path) as connection:
            return int(connection.execute(query, tuple(params)).rowcount)

    def purge_expired(self, retention_seconds: int = 30 * 86_400, now: float | None = None, org_id: str | None = None) -> int:
        current = time.time() if now is None else now
        cutoff = current - max(0, int(retention_seconds))
        query = "DELETE FROM execution_traces WHERE created_at < ?"
        params: list[Any] = [cutoff]
        if org_id is not None:
            query += " AND org_id=?"
            params.append(org_id)
        with sqlite3.connect(self.path) as connection:
            return int(connection.execute(query, tuple(params)).rowcount)

    def get(self, execution_id: str, org_id: str = "development") -> dict | None:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT execution_id, org_id, created_at, status, spans FROM execution_traces WHERE execution_id = ? AND org_id = ?",
                (execution_id, org_id),
            ).fetchone()
        if not row:
            return None
        return {
            "execution_id": row[0],
            "org_id": row[1],
            "created_at": row[2],
            "status": row[3],
            "spans": json.loads(row[4]),
        }
