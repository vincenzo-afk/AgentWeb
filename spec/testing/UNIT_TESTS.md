# Unit Tests

## Coverage expectations
Every module in [../module-specs/](../module-specs/) requires unit tests for:
- Each documented interface method, happy path
- Each documented failure mode (see [../resilience/FAILURE_MODES.md](../resilience/FAILURE_MODES.md))
- Boundary/edge cases (see [../resilience/EDGE_CASES.md](../resilience/EDGE_CASES.md))

## Mocking policy
External I/O (network fetches, store calls) must be mocked at the adapter boundary per [../standards/CODING_STANDARDS.md](../standards/CODING_STANDARDS.md) — unit tests should never make real network calls.

## Example targets
- Planner: task classification accuracy on a labeled fixture set
- Normalizer: correct canonicalization across a matrix of input formats (currencies, date formats, locales)
- Ranking: trust score ordering is stable and monotonic with respect to corroboration count
