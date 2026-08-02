# Style Guide

## Documentation style (this repository)
- Lead with the answer/definition, not preamble.
- Prefer tables for structured comparisons over prose.
- Every spec document links to at least one related document (upstream concept, downstream consumer, or sibling spec).
- Code samples are minimal and runnable-looking, not pseudocode dressed as code, unless explicitly building toward a future/unimplemented API.

## Code style (indicative — finalize with actual toolchain choice)
- Consistent formatter enforced in CI (see [.github/workflows/ci.yml](../../.github/workflows/ci.yml) for the existing validation job as a model to extend).
- Linting treats warnings as errors in CI for anything touching [module-specs](../module-specs/) implementations.

See [CODING_STANDARDS.md](CODING_STANDARDS.md) for substantive (non-formatting) rules.
