"""Local API authentication and rate limiting primitives."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass

from .errors import AuthenticationError, PermissionError, RateLimitError


ALL_SCOPES = {
    "search:read",
    "extract:read",
    "browser:execute",
    "solve:execute",
    "observe:manage",
    "memory:read",
    "admin:*",
}


@dataclass(frozen=True)
class Principal:
    key_id: str
    scopes: frozenset[str]


class Authenticator:
    """Authenticate bearer keys from environment configuration without persisting secrets."""

    def __init__(self) -> None:
        self._keys = self._load_keys()

    @staticmethod
    def _load_keys() -> dict[str, frozenset[str]]:
        configured: dict[str, frozenset[str]] = {}
        single = os.getenv("AGENTWEB_API_KEY")
        if single:
            configured[single] = frozenset(ALL_SCOPES)
        raw = os.getenv("AGENTWEB_API_KEYS")
        if raw:
            try:
                decoded = json.loads(raw)
                if isinstance(decoded, dict):
                    for key, scopes in decoded.items():
                        if isinstance(scopes, str):
                            scopes = [scopes]
                        if isinstance(scopes, list):
                            configured[str(key)] = frozenset(str(scope) for scope in scopes)
            except json.JSONDecodeError:
                pass
        return configured

    def authenticate(self, authorization: str | None, required_scope: str) -> Principal:
        if not self._keys:
            return Principal("development", frozenset(ALL_SCOPES))
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthenticationError("missing or invalid bearer API key")
        token = authorization[7:].strip()
        scopes = self._keys.get(token)
        if scopes is None:
            raise AuthenticationError("missing or invalid bearer API key")
        if required_scope not in scopes and "admin:*" not in scopes:
            raise PermissionError(f"API key lacks required scope: {required_scope}")
        return Principal(token[:8], scopes)


class RateLimiter:
    """Process-local token bucket; deployments can replace it with a shared store."""

    def __init__(self, capacity: float = 100.0, refill_per_second: float = 100.0 / 60.0) -> None:
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def check(self, key_id: str, weight: float = 1.0) -> None:
        now = time.monotonic()
        with self._lock:
            tokens, updated = self._buckets.get(key_id, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - updated) * self.refill_per_second)
            if tokens < weight:
                raise RateLimitError("rate limit exceeded")
            self._buckets[key_id] = (tokens - weight, now)
