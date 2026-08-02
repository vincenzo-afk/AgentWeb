# Acceptance Criteria

## Per-module acceptance criteria (template)
A module is acceptance-tested when:
1. All interface methods documented in its `*_SPEC.md` have passing unit tests, including documented failure modes.
2. It participates correctly in at least one integration test scenario ([INTEGRATION_TESTS.md](INTEGRATION_TESTS.md)).
3. Any invariant from [../decisions/INVARIANTS.md](../decisions/INVARIANTS.md) it touches is explicitly tested, not just assumed.

## Per-endpoint acceptance criteria
An API endpoint is acceptance-tested when it has E2E test coverage for: happy path, each documented error code ([../api/ERROR_CODES.md](../api/ERROR_CODES.md)), and rate-limit/auth boundary behavior.

## Per-milestone acceptance criteria
See [../build-plan/MILESTONES.md](../build-plan/MILESTONES.md) for milestone-level exit criteria, which compose module- and endpoint-level criteria plus [BENCHMARKS.md](BENCHMARKS.md) targets.
