# Retry Policy

## Default policy
Exponential backoff with jitter: `min(base * 2^attempt, max_delay)`, `base = 500ms`, `max_delay = 30s`, `max_attempts = 5` for internal operations; `max_attempts = 3` for outbound fetches to third-party targets (to avoid hammering a struggling site).

## What's retryable
- `upstream_error` (502/503) from a target site — retryable
- Network timeouts — retryable
- `rate_limit_error` (429) — retryable, honoring `X-RateLimit-Reset` if present
- `invalid_request` (400), `authentication_error` (401), `permission_error` (403) — NOT retryable (won't succeed on retry without a change)

## Webhook delivery
Separate, longer-window retry schedule (see [../module-specs/ALERTING_SPEC.md](../module-specs/ALERTING_SPEC.md)): up to 5 attempts over a 24-hour window, since receiving endpoints may be down for longer stretches than a typical upstream fetch target.
