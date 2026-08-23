"""Structured errors shared by the API and platform modules."""

from __future__ import annotations

from .redaction import redact_text


class AgentWebError(Exception):
    """Base error with a stable API-facing type and HTTP status."""

    error_type = "internal_error"
    status_code = 500
    retryable = False

    def __init__(self, message: str, *, request_id: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.request_id = request_id

    def as_dict(self) -> dict:
        error = {"type": self.error_type, "message": redact_text(self.message)}
        if self.request_id:
            error["request_id"] = self.request_id
        return {"error": error}


class InvalidRequestError(AgentWebError):
    error_type = "invalid_request"
    status_code = 400


class AuthenticationError(AgentWebError):
    error_type = "authentication_error"
    status_code = 401


class PermissionError(AgentWebError):
    error_type = "permission_error"
    status_code = 403


class NotFoundError(AgentWebError):
    error_type = "not_found"
    status_code = 404


class ConflictError(AgentWebError):
    error_type = "conflict"
    status_code = 409


class RateLimitError(AgentWebError):
    error_type = "rate_limit_error"
    status_code = 429
    retryable = True

    def __init__(self, message: str, *, retry_after: int | None = None, request_id: str | None = None) -> None:
        super().__init__(message, request_id=request_id)
        self.retry_after = retry_after


class UpstreamError(AgentWebError):
    error_type = "upstream_error"
    status_code = 502
    retryable = True


class BrowserUnavailableError(AgentWebError):
    error_type = "browser_unavailable"
    status_code = 503
    retryable = True


class BrowserActionError(AgentWebError):
    error_type = "browser_action_error"
    status_code = 502
    retryable = True


class BrowserTimeoutError(BrowserActionError):
    error_type = "timeout_error"
