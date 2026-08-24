"""Small structured logging boundary for local and supervised AgentWeb runs."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any, TextIO

from .redaction import redact_mapping, redact_text


_SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "body",
    "content",
    "cookie",
    "credential",
    "credentials",
    "page_content",
    "password",
    "secret",
    "token",
}
_LEVEL_ORDER = {"debug": 10, "info": 20, "warn": 30, "error": 40}
_LEVELS = set(_LEVEL_ORDER)


class StructuredLogger:
    """Emit one bounded JSON object per log line.

    The logger is intentionally a small application boundary rather than a
    hosted logging integration. Callers provide summaries or references, never
    raw page bodies or secret values.
    """

    def __init__(self, stream: TextIO | None = None, clock=time.time, min_level: str = "info") -> None:
        normalized_level = str(min_level).lower().strip()
        if normalized_level not in _LEVELS:
            raise ValueError("min_level must be debug, info, warn, or error")
        self.stream = stream or sys.stderr
        self.clock = clock
        self.min_level = normalized_level
        self._lock = RLock()

    @staticmethod
    def _safe_extra(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(key): StructuredLogger._safe_extra(item)
                for key, item in value.items()
                if str(key).lower() not in _SENSITIVE_KEYS
            }
        if isinstance(value, list):
            return [StructuredLogger._safe_extra(item) for item in value[:20]]
        if isinstance(value, str):
            return redact_text(value)[:500]
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        return redact_text(str(value))[:500]

    def emit(
        self,
        level: str,
        component: str,
        message: str,
        *,
        request_id: str | None = None,
        execution_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        level = str(level).lower().strip()
        if level not in _LEVELS:
            raise ValueError("level must be debug, info, warn, or error")
        record: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(float(self.clock()), tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": level,
            "component": redact_text(str(component))[:120],
            "message": redact_text(str(message))[:500],
        }
        if request_id:
            record["request_id"] = redact_text(str(request_id))[:120]
        if execution_id:
            record["execution_id"] = redact_text(str(execution_id))[:120]
        if extra:
            record["details"] = self._safe_extra(redact_mapping(extra))
        if _LEVEL_ORDER[level] < _LEVEL_ORDER[self.min_level]:
            return record
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            self.stream.write(line + "\n")
            self.stream.flush()
        return record

    def debug(self, component: str, message: str, **kwargs: Any) -> dict[str, Any]:
        return self.emit("debug", component, message, **kwargs)

    def info(self, component: str, message: str, **kwargs: Any) -> dict[str, Any]:
        return self.emit("info", component, message, **kwargs)

    def warn(self, component: str, message: str, **kwargs: Any) -> dict[str, Any]:
        return self.emit("warn", component, message, **kwargs)

    def error(self, component: str, message: str, **kwargs: Any) -> dict[str, Any]:
        return self.emit("error", component, message, **kwargs)


__all__ = ["StructuredLogger"]
