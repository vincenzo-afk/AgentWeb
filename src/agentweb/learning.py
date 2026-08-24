"""Privacy-safe outcome persistence for the local learning loop."""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class LearningStore:
    """Persist outcome signals, never raw task text or source content."""

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
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS learning_outcomes (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    execution_id TEXT,
                    success INTEGER NOT NULL,
                    evidence_score REAL NOT NULL,
                    latency_ms INTEGER,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_learning_org_strategy
                    ON learning_outcomes(org_id, strategy, mode, created_at DESC);
                """
            )

    @staticmethod
    def _validate_strategy(strategy: str) -> str:
        value = str(strategy or "").strip()
        if not value or len(value) > 120:
            raise ValueError("strategy must contain between 1 and 120 characters")
        return value

    @staticmethod
    def _validate_mode(mode: str) -> str:
        value = str(mode or "focus").strip()
        if value not in {"flash", "focus", "dive", "monitor"}:
            raise ValueError("mode must be flash, focus, dive, or monitor")
        return value

    def record_outcome(
        self,
        strategy: str,
        mode: str,
        success: bool,
        evidence_score: float,
        org_id: str = "development",
        execution_id: str | None = None,
        latency_ms: int | None = None,
        created_at: float | None = None,
    ) -> dict[str, Any]:
        strategy = self._validate_strategy(strategy)
        mode = self._validate_mode(mode)
        try:
            evidence_score = float(evidence_score)
        except (TypeError, ValueError) as error:
            raise ValueError("evidence_score must be numeric") from error
        if not 0.0 <= evidence_score <= 1.0:
            raise ValueError("evidence_score must be between 0 and 1")
        if latency_ms is not None and (isinstance(latency_ms, bool) or int(latency_ms) < 0 or int(latency_ms) > 86_400_000):
            raise ValueError("latency_ms must be between 0 and 86400000")
        now = time.time() if created_at is None else float(created_at)
        outcome_id = "outcome_" + uuid.uuid4().hex[:16]
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO learning_outcomes(id, org_id, strategy, mode, execution_id, success, evidence_score, latency_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (outcome_id, org_id, strategy, mode, execution_id, int(bool(success)), evidence_score, int(latency_ms) if latency_ms is not None else None, now),
            )
        return {
            "id": outcome_id,
            "org_id": org_id,
            "strategy": strategy,
            "mode": mode,
            "execution_id": execution_id,
            "success": bool(success),
            "evidence_score": evidence_score,
            "latency_ms": int(latency_ms) if latency_ms is not None else None,
            "created_at": now,
        }

    def summary(self, org_id: str = "development", limit: int = 100) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(int(limit), 100))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT strategy, mode, COUNT(*) AS observations, AVG(success) AS success_rate, AVG(evidence_score) AS average_evidence_score, AVG(latency_ms) AS average_latency_ms, MAX(created_at) AS last_observed_at FROM learning_outcomes WHERE org_id=? GROUP BY strategy, mode ORDER BY observations DESC, strategy, mode LIMIT ?",
                (org_id, bounded_limit),
            ).fetchall()
        return [
            {
                "strategy": row["strategy"],
                "mode": row["mode"],
                "observations": int(row["observations"]),
                "success_rate": round(float(row["success_rate"]), 4),
                "average_evidence_score": round(float(row["average_evidence_score"]), 4),
                "average_latency_ms": round(float(row["average_latency_ms"]), 2) if row["average_latency_ms"] is not None else None,
                "last_observed_at": row["last_observed_at"],
            }
            for row in rows
        ]

    def health(self) -> bool:
        try:
            with self._connect() as connection:
                return connection.execute("SELECT 1").fetchone()[0] == 1
        except (OSError, sqlite3.Error):
            return False
