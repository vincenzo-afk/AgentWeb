"""Site-specific connector registration and deterministic URL matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class Connector:
    name: str
    pattern: str
    extraction_hints: dict[str, Any] = field(default_factory=dict)
    interaction_script: list[dict[str, Any]] = field(default_factory=list)
    ranking_bias: dict[str, list[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name.strip()) > 120:
            raise ValueError("connector name must contain between 1 and 120 characters")
        if not isinstance(self.pattern, str) or not self.pattern.strip() or len(self.pattern.strip()) > 500:
            raise ValueError("connector pattern must contain between 1 and 500 characters")
        if not isinstance(self.extraction_hints, dict):
            raise ValueError("extraction_hints must be an object")
        if not isinstance(self.interaction_script, list) or len(self.interaction_script) > 20:
            raise ValueError("interaction_script must be an array with at most 20 actions")
        if not isinstance(self.ranking_bias, dict):
            raise ValueError("ranking_bias must be an object")
        unknown = set(self.ranking_bias) - {"boost", "penalize"}
        if unknown:
            raise ValueError(f"unsupported ranking_bias field: {sorted(unknown)[0]}")
        for key in ("boost", "penalize"):
            values = self.ranking_bias.get(key, [])
            if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"ranking_bias.{key} must be an array of non-empty strings")

    @property
    def normalized_pattern(self) -> str:
        return self.pattern.strip().lower().rstrip("/")

    @property
    def specificity(self) -> int:
        return len(self.normalized_pattern)

    def match(self, url: str) -> bool:
        if not isinstance(url, str) or not url.strip():
            return False
        candidate = url.strip().lower().rstrip("/")
        pattern = self.normalized_pattern
        if "://" in pattern:
            return candidate == pattern or candidate.startswith(pattern + "/")
        host = urlparse(candidate).netloc.split(":", 1)[0]
        return host == pattern or host.endswith("." + pattern)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "pattern": self.pattern,
            "extraction_hints": self.extraction_hints,
            "interaction_script": self.interaction_script,
            "ranking_bias": self.ranking_bias,
        }


class ConnectorRegistry:
    """Thread-safe registry selecting the most-specific matching connector."""

    def __init__(self, connectors: list[Connector] | None = None) -> None:
        self._lock = RLock()
        self._connectors: dict[str, Connector] = {}
        for connector in connectors or []:
            self.register(connector)

    def register(self, connector: Connector) -> Connector:
        if not isinstance(connector, Connector):
            raise TypeError("connector must be a Connector")
        with self._lock:
            if connector.name in self._connectors:
                raise ValueError(f"connector already registered: {connector.name}")
            self._connectors[connector.name] = connector
        return connector

    def unregister(self, name: str) -> bool:
        with self._lock:
            return self._connectors.pop(name, None) is not None

    def get(self, name: str) -> Connector | None:
        with self._lock:
            return self._connectors.get(name)

    def list(self) -> list[Connector]:
        with self._lock:
            return sorted(self._connectors.values(), key=lambda item: (-item.specificity, item.name))

    def match(self, url: str) -> Connector | None:
        with self._lock:
            matches = [connector for connector in self._connectors.values() if connector.match(url)]
        return min(matches, key=lambda item: (-item.specificity, item.name), default=None)
