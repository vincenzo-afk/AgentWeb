"""Webhook alert delivery with HMAC signing and bounded retry behavior."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from http.client import HTTPResponse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class DeliveryResult:
    delivered: bool
    attempts: int
    status_code: int | None = None
    error: str | None = None
    response_ids: list[str] = field(default_factory=list)


def signature(raw_body: bytes, timestamp: str, signing_secret: str) -> str:
    """Return a replay-resistant HMAC-SHA256 signature for a webhook body."""
    message = f"{timestamp}.".encode("utf-8") + raw_body
    digest = hmac.new(signing_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def _read_status(response: HTTPResponse) -> int:
    return int(getattr(response, "status", response.getcode()))


def send_webhook(
    url: str,
    payload: dict,
    signing_secret: str,
    *,
    max_attempts: int = 5,
    timeout: float = 10.0,
    backoff_seconds: float = 0.5,
) -> DeliveryResult:
    """Send a signed JSON webhook, retrying non-2xx/network failures with bounded backoff."""
    if not signing_secret:
        return DeliveryResult(False, 0, error="webhook signing secret is required")
    raw_body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    timestamp = str(int(time.time()))
    signed = signature(raw_body, timestamp, signing_secret)
    last_error: str | None = None
    last_status: int | None = None
    for attempt in range(1, max(1, max_attempts) + 1):
        request = Request(
            url,
            data=raw_body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AgentWeb/0.1",
                "X-AgentWeb-Signature": signed,
                "X-AgentWeb-Timestamp": timestamp,
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                last_status = _read_status(response)
            if 200 <= last_status < 300:
                return DeliveryResult(True, attempt, status_code=last_status)
            last_error = f"webhook returned HTTP {last_status}"
        except HTTPError as error:
            last_status = error.code
            last_error = f"webhook returned HTTP {error.code}"
        except (URLError, TimeoutError, OSError) as error:
            last_error = str(error)
        if attempt < max_attempts:
            time.sleep(min(backoff_seconds * (2 ** (attempt - 1)), 30.0))
    return DeliveryResult(False, max(1, max_attempts), status_code=last_status, error=last_error)
