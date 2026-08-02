# Resource Limits

| Resource | Limit | Rationale |
|---|---|---|
| Browser session memory | Capped per session | Bounds blast radius of a resource-heavy or adversarial page ([../../docs/security/sandboxing.md](../../docs/security/sandboxing.md)) |
| Browser session CPU time | Capped, tied to [TIMEOUT_POLICY](../resilience/TIMEOUT_POLICY.md) | Prevents runaway JS execution from a malicious/inefficient page |
| Concurrent browser sessions per organization | Capped by plan tier | Prevents one organization from starving the shared worker pool |
| Crawl `max_pages` | Capped (default per [../config/DEFAULTS.md](../config/DEFAULTS.md), override-able) | Bounds cost/time of a single crawl request |
| Snapshot size per target | Capped | Bounds storage growth per target; oversized content truncated with a flag |

Limits are enforced at the primitive level (Search/Crawl/Browser/Extract), not just at the API gateway, so internal callers can't bypass them.
