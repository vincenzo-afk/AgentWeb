"""Small, deterministic redaction helpers for diagnostics and persisted metadata."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_SECRET_QUERY_NAMES = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "key",
    "password",
    "secret",
    "sig",
    "signature",
    "token",
}
_URL_RE = re.compile(r"https?://[^\s)\]>]+")
_SECRET_PATTERNS = (
    (re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+"), r"\1[REDACTED]"),
    (re.compile(r"\bsk-(?:live|test)-[A-Za-z0-9_-]+\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"(?i)(password|secret|token|api[_-]?key)\s*[:=]\s*[^\s,;]+"), r"\1=[REDACTED]"),
)


def redact_url(value: str) -> str:
    """Remove URL userinfo and redact values of credential-like query parameters."""
    if not isinstance(value, str):
        return value
    try:
        parsed = urlsplit(value)
        if not parsed.scheme or not parsed.netloc:
            return redact_text(value)
        hostname = parsed.hostname or ""
        host = hostname
        if ":" in hostname and not hostname.startswith("["):
            host = f"[{hostname}]"
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        query = []
        for name, item in parse_qsl(parsed.query, keep_blank_values=True):
            query.append((name, "[REDACTED]" if name.lower() in _SECRET_QUERY_NAMES else item))
        return urlunsplit((parsed.scheme, host, parsed.path, urlencode(query), ""))
    except (TypeError, ValueError):
        return redact_text(value)


def redact_text(value: str) -> str:
    """Redact common secret representations without attempting to preserve values."""
    if not isinstance(value, str):
        return value
    result = value
    for pattern, replacement in _SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    return _URL_RE.sub(lambda match: redact_url(match.group(0)), result)[:2000]


def redact_mapping(value):
    """Recursively redact strings in JSON-like diagnostic values."""
    if isinstance(value, dict):
        return {key: redact_mapping(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_mapping(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value
