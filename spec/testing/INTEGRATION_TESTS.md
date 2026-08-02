# Integration Tests

## Scope
Real connections to storage layers ([../data/STORAGE_SPEC.md](../data/STORAGE_SPEC.md)) and the job queue ([../data/QUEUE_SPEC.md](../data/QUEUE_SPEC.md)), but mocked external (third-party) targets, so tests are deterministic and don't depend on live internet content.

## Key scenarios
- Memory snapshot write → read → diff round-trip
- Graph entity upsert → query round-trip with corroboration accumulation
- Monitor scheduling → check → alert delivery, using a mock target that changes on the second check
- Idempotency key reuse returning cached result vs. `409` on payload mismatch

## Test fixtures
Maintain a stable set of mock target pages (HTML fixtures) representing common patterns (product page, docs page, JS-rendered SPA) for consistent integration coverage.
