# Trust Engine Spec

## Purpose
Platform-level safety gating — distinct from per-source ranking. See [docs/core/trust-and-safety.md](../../docs/core/trust-and-safety.md).

## Interface
```
should_fetch(url: string) -> { allowed: bool, reason?: string }
should_surface(content: NormalizedContent) -> { allowed: bool, reason?: string }
```

## Gating rules
- Respect `robots.txt` and site terms where applicable.
- Block known malware/phishing-associated domains.
- Rate-limit outbound requests per target domain (see [../../docs/api/rate-limits.md](../../docs/api/rate-limits.md) for the customer-facing analog).
- Filter synthesis output for content violating usage policy.

## Failure modes
Ambiguous cases (e.g., unclear terms of service) default to allow with a logged flag for review, rather than blocking silently — see [../resilience/EDGE_CASES.md](../resilience/EDGE_CASES.md).
