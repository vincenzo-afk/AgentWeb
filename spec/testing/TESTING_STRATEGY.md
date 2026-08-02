# Testing Strategy

## Test pyramid

1. **Unit tests** — per-module, mocked dependencies. See [UNIT_TESTS.md](UNIT_TESTS.md).
2. **Integration tests** — real store connections, mocked external targets. See [INTEGRATION_TESTS.md](INTEGRATION_TESTS.md).
3. **System tests** — full pipeline against a controlled test-fixture website. See [SYSTEM_TESTS.md](SYSTEM_TESTS.md).
4. **End-to-end tests** — real API calls against real (or near-real) targets in staging. See [E2E_TESTS.md](E2E_TESTS.md).

## Special test categories
- **Benchmarks** for latency/cost per mode — see [BENCHMARKS.md](BENCHMARKS.md) and [PERFORMANCE_TARGETS.md](PERFORMANCE_TARGETS.md).
- **Load tests** for scaling/capacity validation — see [LOAD_TESTS.md](LOAD_TESTS.md).

## Definition of "tested enough to ship"
See [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md), [DONE_DEFINITION.md](DONE_DEFINITION.md), and [QUALITY_GATES.md](QUALITY_GATES.md).
