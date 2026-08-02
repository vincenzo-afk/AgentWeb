# End-to-End Tests

## Scope
Real API calls (via the public REST interface, not internal function calls) against staging infrastructure, optionally against a small set of stable real-world targets in addition to fixtures.

## What E2E tests validate that lower-level tests don't
- Auth, rate limiting, and idempotency behavior through the actual API tier (not bypassed via internal test harnesses)
- SDK correctness ([../../docs/sdk/index.md](../../docs/sdk/index.md)) — SDK calls should produce identical results to raw REST calls
- Webhook delivery to a real (test) receiving endpoint, including signature verification

## Cadence
Run against staging on every release candidate; a curated subset runs against production periodically as a synthetic-monitoring health check (see [../../docs/operations/monitoring-stack.md](../../docs/operations/monitoring-stack.md)).
