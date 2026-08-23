"""Append-only, secret-safe execution trace records."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path


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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_traces (
                    execution_id TEXT PRIMARY KEY,
                    created_at REAL NOT NULL,
                    status TEXT NOT NULL,
                    spans TEXT NOT NULL
                )
                """
            )

    def start(self) -> str:
        return "exec_" + uuid.uuid4().hex[:16]

    def save(self, execution_id: str, spans: list[Span], status: str = "complete") -> None:
        payload = json.dumps([asdict(span) for span in spans], separators=(",", ":"))
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO execution_traces(execution_id, created_at, status, spans) VALUES (?, ?, ?, ?)",
                (execution_id, time.time(), status, payload),
            )

    def get(self, execution_id: str) -> dict | None:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT execution_id, created_at, status, spans FROM execution_traces WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "execution_id": row[0],
            "created_at": row[1],
            "status": row[2],
            "spans": json.loads(row[3]),
        }
