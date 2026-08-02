# Constraints

## Technical constraints
- Browser sessions are the most resource-intensive execution primitive and must be sandboxed per-request (see [../../docs/security/sandboxing.md](../../docs/security/sandboxing.md)) — this caps horizontal scaling headroom relative to lighter primitives like Search.
- Third-party sites are outside AgentWeb's control; availability, structure, and rate-limiting behavior of targets constrain achievable latency and reliability ([../resilience/FAILURE_MODES.md](../resilience/FAILURE_MODES.md)).
- Snapshot/graph storage must scale with organization usage over time; retention policy ([../../docs/operations/data-retention.md](../../docs/operations/data-retention.md)) exists partly to bound this growth.

## Product constraints
- The outcome-first API must not silently exceed a customer's expected cost tier without an explicit opt-in (see [../../docs/operations/cost-controls.md](../../docs/operations/cost-controls.md)).
- Explainability guarantees (citations, execution graphs) apply to all modes, including `flash` — cannot be traded away for speed.

## Legal/compliance constraints
- Crawling/browsing must respect `robots.txt` and site terms where applicable ([../module-specs/TRUST_ENGINE_SPEC.md](../module-specs/TRUST_ENGINE_SPEC.md)).
