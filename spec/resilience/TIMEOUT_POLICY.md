# Timeout Policy

| Operation | Timeout |
|---|---|
| Search query | 5s |
| Static page fetch | 10s |
| Single browser action (click/wait/extract) | 30s |
| Full browser session | 90s |
| Extraction (per page) | 15s |
| `flash` mode overall | 2s target (see [../testing/PERFORMANCE_TARGETS.md](../testing/PERFORMANCE_TARGETS.md)) |
| `focus` mode overall | 8s target |
| `dive` mode overall | 60s soft target; beyond this, recommend async/webhook delivery |
| Monitor check | Same as the underlying fetch/browser timeout for that target |
| Webhook delivery attempt | 10s |

Timeouts trigger the [RETRY_POLICY.md](RETRY_POLICY.md) path, not immediate failure, except where retries are exhausted.
