"""Bounded organization-scoped metrics with an optional durable SQLite store."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


class MetricStore:
    """Small local-first metric store; rows are updated atomically per metric key."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS metric_points ("
                "org_id TEXT NOT NULL, metric_key TEXT NOT NULL, kind TEXT NOT NULL, "
                "counter INTEGER NOT NULL DEFAULT 0, sample_count INTEGER NOT NULL DEFAULT 0, "
                "sample_sum REAL NOT NULL DEFAULT 0, gauge_value REAL, updated_at REAL NOT NULL, "
                "PRIMARY KEY(org_id, metric_key, kind))"
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_metric_points_org_time ON metric_points(org_id, updated_at)")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _org(labels: dict[str, Any] | None) -> str:
        return str((labels or {}).get("org_id") or "__global__")

    def increment(self, key: str, value: int, labels: dict[str, Any] | None = None) -> None:
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO metric_points(org_id, metric_key, kind, counter, updated_at) VALUES(?, ?, 'counter', ?, ?) "
                "ON CONFLICT(org_id, metric_key, kind) DO UPDATE SET counter=counter+excluded.counter, updated_at=excluded.updated_at",
                (self._org(labels), key, int(value), now),
            )

    def observe(self, key: str, value: float, labels: dict[str, Any] | None = None) -> None:
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO metric_points(org_id, metric_key, kind, sample_count, sample_sum, updated_at) VALUES(?, ?, 'observation', 1, ?, ?) "
                "ON CONFLICT(org_id, metric_key, kind) DO UPDATE SET sample_count=sample_count+1, sample_sum=sample_sum+excluded.sample_sum, updated_at=excluded.updated_at",
                (self._org(labels), key, float(value), now),
            )

    def gauge(self, key: str, value: float, labels: dict[str, Any] | None = None) -> None:
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO metric_points(org_id, metric_key, kind, gauge_value, updated_at) VALUES(?, ?, 'gauge', ?, ?) "
                "ON CONFLICT(org_id, metric_key, kind) DO UPDATE SET gauge_value=excluded.gauge_value, updated_at=excluded.updated_at",
                (self._org(labels), key, float(value), now),
            )

    def snapshot(self, org_id: str | None = None) -> dict[str, dict[str, float | int]]:
        with self._connect() as connection:
            if org_id is None:
                rows = connection.execute("SELECT org_id, metric_key, kind, counter, sample_count, sample_sum, gauge_value FROM metric_points").fetchall()
            else:
                rows = connection.execute("SELECT org_id, metric_key, kind, counter, sample_count, sample_sum, gauge_value FROM metric_points WHERE org_id = ?", (org_id,)).fetchall()
        counters: dict[str, int] = {}
        observations: dict[str, dict[str, float | int]] = {}
        gauges: dict[str, float] = {}
        for row in rows:
            key = str(row["metric_key"])
            if row["org_id"] != "__global__":
                labels = json.loads(key.split("|", 1)[1]) if "|" in key else {}
                label_suffix = ",".join(f"{name}={labels[name]}" for name in sorted(labels))
                display_key = key.split("|", 1)[0] + (f"{{{label_suffix}}}" if label_suffix else "")
            else:
                display_key = key.split("|", 1)[0] if "|" in key else key
            if row["kind"] == "counter":
                counters[display_key] = int(row["counter"])
            elif row["kind"] == "observation":
                observations[display_key] = {"count": int(row["sample_count"]), "sum": float(row["sample_sum"])}
            else:
                gauges[display_key] = float(row["gauge_value"] or 0.0)
        return {"counters": counters, "observations": observations, "gauges": gauges, "captured_at": time.time()}

    def purge_expired(self, retention_seconds: float, now: float | None = None, org_id: str | None = None) -> int:
        if retention_seconds < 0:
            raise ValueError("metric retention cannot be negative")
        cutoff = (time.time() if now is None else now) - retention_seconds
        with self._connect() as connection:
            if org_id is None:
                cursor = connection.execute("DELETE FROM metric_points WHERE updated_at < ?", (cutoff,))
            else:
                cursor = connection.execute("DELETE FROM metric_points WHERE org_id = ? AND updated_at < ?", (org_id, cutoff))
        return cursor.rowcount


class MetricsRegistry:
    def __init__(self, store: MetricStore | None = None) -> None:
        self.store = store
        self._lock = threading.Lock()
        self._counters: defaultdict[str, int] = defaultdict(int)
        self._sums: defaultdict[str, float] = defaultdict(float)
        self._observation_counts: defaultdict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}

    @staticmethod
    def _key(name: str, labels: dict[str, Any] | None = None) -> str:
        normalized = labels or {}
        suffix = json.dumps({key: normalized[key] for key in sorted(normalized)}, sort_keys=True, separators=(",", ":"))
        return f"{name}|{suffix}" if normalized else name

    def increment(self, name: str, value: int = 1, labels: dict[str, Any] | None = None) -> None:
        if self.store:
            self.store.increment(self._key(name, labels), value, labels)
            return
        with self._lock:
            self._counters[self._key(name, labels)] += int(value)

    def observe(self, name: str, value: float, labels: dict[str, Any] | None = None) -> None:
        if self.store:
            self.store.observe(self._key(name, labels), value, labels)
            return
        with self._lock:
            key = self._key(name, labels)
            self._observation_counts[key] += 1
            self._sums[key] += float(value)

    def gauge(self, name: str, value: float, labels: dict[str, Any] | None = None) -> None:
        if self.store:
            self.store.gauge(self._key(name, labels), value, labels)
            return
        with self._lock:
            self._gauges[self._key(name, labels)] = float(value)

    def record_request(self, endpoint: str, elapsed_seconds: float, status: int, org_id: str | None = None, error_type: str | None = None) -> None:
        labels = {"endpoint": endpoint}
        if org_id:
            labels["org_id"] = org_id
        self.increment("request_count", labels=labels)
        self.observe("request_latency", elapsed_seconds, labels=labels)
        if status >= 400:
            error_labels = {"type": error_type or str(status), "endpoint": endpoint}
            if org_id:
                error_labels["org_id"] = org_id
            self.increment("error_count", labels=error_labels)

    def snapshot(self, org_id: str | None = None) -> dict[str, dict[str, float | int]]:
        if self.store:
            return self.store.snapshot(org_id)
        def visible(key: str) -> bool:
            return org_id is None or f'"org_id":"{org_id}"' in key
        with self._lock:
            return {
                "counters": {key: value for key, value in self._counters.items() if visible(key)},
                "observations": {key: {"count": self._observation_counts[key], "sum": value} for key, value in self._sums.items() if visible(key)},
                "gauges": {key: value for key, value in self._gauges.items() if visible(key)},
                "captured_at": time.time(),
            }

    def purge_expired(self, retention_seconds: float, now: float | None = None, org_id: str | None = None) -> int:
        return self.store.purge_expired(retention_seconds, now=now, org_id=org_id) if self.store else 0
