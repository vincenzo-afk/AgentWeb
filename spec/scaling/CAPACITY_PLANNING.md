# Capacity Planning

## Method
Project peak QPS per mode/primitive from expected customer growth, validate against [../testing/LOAD_TESTS.md](../testing/LOAD_TESTS.md) results, and provision with margin (target: sustain projected peak at no more than 70% of max validated capacity per component).

## Highest-risk component
Browser worker pool — most expensive to over-provision (idle cost) and most damaging to under-provision (cascades into [../resilience/CIRCUIT_BREAKERS.md](../resilience/CIRCUIT_BREAKERS.md) engaging and degraded extraction quality via [../resilience/FALLBACKS.md](../resilience/FALLBACKS.md)).

## Review cadence
Capacity plan reviewed each time a new [milestone](../build-plan/MILESTONES.md) ships, since new capabilities (e.g., Graph GA) shift load patterns across components.
