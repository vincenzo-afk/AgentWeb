# Rate Limits

Rate limits are applied per API key and vary by endpoint and retrieval mode (deeper modes like `dive` consume more of your quota per call than `flash`).

Response headers on every request:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 82
X-RateLimit-Reset: 1735660800
```

On exceeding a limit, requests return `429 rate_limit_error`. Clients should respect `X-RateLimit-Reset` and use exponential backoff for retries.

Monitors created via `/observe` count against a separate scheduled-execution quota rather than your interactive request quota. See [reference/monitor.md](reference/monitor.md).
