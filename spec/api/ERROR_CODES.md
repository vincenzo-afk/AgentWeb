# Error Codes

See [docs/api/errors.md](../../docs/api/errors.md) for the prose reference.

| HTTP | `type` | Retryable? |
|---|---|---|
| 400 | `invalid_request` | No — fix the request |
| 401 | `authentication_error` | No — fix credentials |
| 403 | `permission_error` | No — insufficient scope |
| 404 | `not_found` | No |
| 409 | `conflict` | No — idempotency key reuse mismatch |
| 429 | `rate_limit_error` | Yes — after `X-RateLimit-Reset` |
| 500 | `internal_error` | Yes — with backoff |
| 502/503 | `upstream_error` | Yes — the target source, not AgentWeb, is likely at fault |

## Client guidance
Only 429/500/502/503 should be retried automatically; all others indicate a request that needs to change before retrying. See [../resilience/RETRY_POLICY.md](../resilience/RETRY_POLICY.md) for backoff parameters.
