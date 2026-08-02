# Cache Spec

## Purpose
Short-lived, high-speed caching layer distinct from the durable [Memory](../module-specs/MEMORY_SPEC.md) snapshot store — reduces latency for repeated identical calls within a short window, rather than tracking change over time.

## What's cached
- Search results for identical queries (TTL: minutes)
- API key scope lookups (TTL: seconds, to reduce DB load per request)
- Rate limit counters (see [../api/RATE_LIMITS.md](../api/RATE_LIMITS.md))

## What's NOT cached here
Page snapshots and extraction results — those belong in the durable Memory store since they need hash-based comparison over long time horizons, not just fast repeated reads.

## Eviction
TTL-based; no manual invalidation required given short TTLs.
