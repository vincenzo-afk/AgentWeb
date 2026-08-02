# Load Tests

## Scenarios
- Sustained request volume at target QPS per mode, verifying latency targets hold under load (not just at idle).
- Burst load (sudden spike) — verify rate limiting and circuit breakers ([../resilience/CIRCUIT_BREAKERS.md](../resilience/CIRCUIT_BREAKERS.md)) engage correctly rather than cascading failures.
- High monitor volume — verify scheduler correctly prioritizes `minutely` over `daily` monitors under queue backlog (see [../data/QUEUE_SPEC.md](../data/QUEUE_SPEC.md)).
- Browser worker pool saturation — verify graceful degradation/fallback ([../resilience/FALLBACKS.md](../resilience/FALLBACKS.md)) rather than unbounded queueing.

## Capacity validation
Load test results feed [../scaling/CAPACITY_PLANNING.md](../scaling/CAPACITY_PLANNING.md) — the max sustainable QPS per component observed here should exceed projected production peak with margin.
