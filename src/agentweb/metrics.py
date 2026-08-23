"""Bounded in-process metrics for the local MVP and worker diagnostics."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: defaultdict[str, int] = defaultdict(int)
        self._sums: defaultdict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}

    @staticmethod
    def _key(name: str, labels: dict[str, Any] | None = None) -> str:
        normalized = labels or {}
        suffix = ",".join(f"{key}={normalized[key]}" for key in sorted(normalized))
        return f"{name}{{{suffix}}}" if suffix else name

    def increment(self, name: str, value: int = 1, labels: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._counters[self._key(name, labels)] += int(value)

    def observe(self, name: str, value: float, labels: dict[str, Any] | None = None) -> None:
        with self._lock:
            key = self._key(name, labels)
            self._counters[key + ".count"] += 1
            self._sums[key + ".sum"] += float(value)

    def gauge(self, name: str, value: float, labels: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._gauges[self._key(name, labels)] = float(value)

    def record_request(self, endpoint: str, elapsed_seconds: float, status: int, org_id: str | None = None, error_type: str | None = None) -> None:
        labels = {"endpoint": endpoint}
        if org_id:
            labels["org_id"] = org_id
        self.increment("request_count", labels=labels)
        self.observe("request_latency", elapsed_seconds, labels=labels)
        if status >= 400:
            self.increment("error_count", labels={"type": error_type or str(status), "endpoint": endpoint})

    def snapshot(self, org_id: str | None = None) -> dict[str, dict[str, float | int]]:
        def visible(key: str) -> bool:
            return org_id is None or f"org_id={org_id}" in key or "org_id=" not in key

        with self._lock:
            return {
                "counters": {key: value for key, value in self._counters.items() if visible(key)},
                "observations": {
                    key: {"count": self._counters[key + ".count"], "sum": value}
                    for key, value in self._sums.items()
                    if visible(key)
                },
                "gauges": {key: value for key, value in self._gauges.items() if visible(key)},
                "captured_at": time.time(),
            }
