# Errors

Errors follow a consistent JSON shape with a standard HTTP status code:

```json
{
  "error": {
    "type": "invalid_request",
    "message": "task is required",
    "request_id": "req_abc123"
  }
}
```

## Common error types

| HTTP status | `type` | Meaning |
|---|---|---|
| 400 | `invalid_request` | Malformed or missing required fields |
| 401 | `authentication_error` | Missing/invalid API key |
| 403 | `permission_error` | Key lacks scope for this operation |
| 404 | `not_found` | Resource (run, monitor, target) doesn't exist |
| 409 | `conflict` | Idempotency key reused with different payload |
| 429 | `rate_limit_error` | Too many requests; see [rate-limits.md](rate-limits.md) |
| 500 | `internal_error` | Unexpected server-side failure |
| 502/503 | `upstream_error` | A downstream source (e.g., a browsed page) failed to respond |

Always include `request_id` when contacting support about a specific failure.
