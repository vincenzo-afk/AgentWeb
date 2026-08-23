"""External platform-secret resolution with fail-closed production behavior."""

from __future__ import annotations

import os
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Mapping, Protocol


class SecretProviderError(RuntimeError):
    """Raised when a required platform secret cannot be resolved safely."""


class SecretProvider(Protocol):
    def get(self, name: str, required: bool = True) -> str | None:
        ...


_SECRET_NAME_RE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")


@dataclass(frozen=True)
class SecretProviderConfig:
    environment: str
    provider_name: str
    ttl_seconds: float = 30.0
    command: str | None = None

    @classmethod
    def from_environment(cls) -> "SecretProviderConfig":
        environment = os.getenv("AGENTWEB_ENV", "development").strip().lower()
        if environment not in {"development", "staging", "production"}:
            raise SecretProviderError("AGENTWEB_ENV must be development, staging, or production")
        provider_name = os.getenv("AGENTWEB_SECRET_PROVIDER", "env" if environment == "development" else "")
        if provider_name not in {"env", "mapping", "command"}:
            raise SecretProviderError("AGENTWEB_SECRET_PROVIDER must be env, mapping, or command")
        if environment != "development" and provider_name == "env":
            raise SecretProviderError("environment secrets are not allowed outside development")
        try:
            ttl = float(os.getenv("AGENTWEB_SECRET_TTL_SECONDS", "30"))
        except ValueError as error:
            raise SecretProviderError("AGENTWEB_SECRET_TTL_SECONDS must be numeric") from error
        return cls(environment, provider_name, max(0.0, min(ttl, 300.0)), os.getenv("AGENTWEB_SECRET_COMMAND"))


class _BaseProvider:
    def __init__(self, ttl_seconds: float = 30.0) -> None:
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()

    def _cached(self, name: str) -> str | None:
        with self._lock:
            item = self._cache.get(name)
            if item and item[0] > time.monotonic():
                return item[1]
            if item:
                self._cache.pop(name, None)
        return None

    def _remember(self, name: str, value: str) -> str:
        with self._lock:
            self._cache[name] = (time.monotonic() + self.ttl_seconds, value)
        return value

    def _resolve(self, name: str) -> str | None:
        raise NotImplementedError

    def get(self, name: str, required: bool = True) -> str | None:
        _validate_name(name)
        cached = self._cached(name)
        value = cached if cached is not None else self._resolve(name)
        if value is not None:
            value = str(value).strip()
            if value:
                return self._remember(name, value)
        if required:
            raise SecretProviderError(f"required secret is unavailable: {name}")
        return None


class EnvironmentSecretProvider(_BaseProvider):
    def _resolve(self, name: str) -> str | None:
        return os.getenv(name)


class MappingSecretProvider(_BaseProvider):
    def __init__(self, values: Mapping[str, str], ttl_seconds: float = 30.0) -> None:
        super().__init__(ttl_seconds)
        self.values = dict(values)

    def _resolve(self, name: str) -> str | None:
        return self.values.get(name)


class CommandSecretProvider(_BaseProvider):
    def __init__(self, command: str, ttl_seconds: float = 30.0) -> None:
        super().__init__(ttl_seconds)
        if not command.strip():
            raise SecretProviderError("AGENTWEB_SECRET_COMMAND is required for the command provider")
        self.command = command

    def _resolve(self, name: str) -> str | None:
        try:
            completed = subprocess.run(
                [self.command, name],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise SecretProviderError(f"secret provider command failed for {name}: {type(error).__name__}") from error
        if completed.returncode != 0:
            raise SecretProviderError(f"secret provider command rejected {name}")
        return completed.stdout.strip()


def _validate_name(name: str) -> None:
    if not name or len(name) > 128 or any(char not in _SECRET_NAME_RE for char in name):
        raise SecretProviderError("invalid secret name")


def build_provider(values: Mapping[str, str] | None = None) -> SecretProvider:
    config = SecretProviderConfig.from_environment()
    if values is not None:
        return MappingSecretProvider(values, config.ttl_seconds)
    if config.provider_name == "mapping":
        raise SecretProviderError("mapping secret provider requires injected values")
    if config.provider_name == "command":
        return CommandSecretProvider(config.command or "", config.ttl_seconds)
    return EnvironmentSecretProvider(config.ttl_seconds)


def require_production_secrets(provider: SecretProvider, names: list[str]) -> dict[str, str]:
    return {name: provider.get(name, required=True) or "" for name in names}
