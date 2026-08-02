# Circuit Breakers

## Per-target-domain breaker
If a specific domain returns errors/timeouts above a threshold rate within a rolling window, the Router temporarily stops sending new requests to that domain (returning a fast `upstream_error` instead of attempting and timing out) and periodically probes to detect recovery. This protects both AgentWeb's own resource usage and avoids adding load to an already-struggling third-party site.

## Per-execution-primitive breaker
If Browser session failures spike system-wide (e.g., due to a sandboxing infrastructure issue), a breaker can temporarily route Router decisions away from Browser escalation toward static-fetch-only, degrading quality for JS-heavy pages rather than failing those requests outright — see [FALLBACKS.md](FALLBACKS.md).

## Recovery
Breakers use a half-open probe pattern: after a cooldown period, a limited number of requests are allowed through to test recovery before fully closing the breaker.
