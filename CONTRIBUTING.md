# Contributing to AgentWeb

Thanks for your interest in improving AgentWeb. This document covers how to propose changes, report issues, and submit code.

## Ways to contribute

- **Bug reports** — use the bug report issue template and include reproduction steps.
- **Feature proposals** — for anything beyond a small fix, open an issue first so we can discuss scope before you write code. Larger architectural proposals should follow the RFC process (see `docs/rfcs` if present, or open a discussion issue).
- **Documentation** — fixes to `docs/`, `examples/`, or the API reference are always welcome and reviewed faster than code changes.
- **Connectors and skills** — see [Building Connectors](docs/guides/building-connectors.md) and [Creating Skills](docs/guides/creating-skills.md).

## Development setup

1. Fork and clone the repository.
2. Install dependencies for the component you're working on (SDK, core services, or docs tooling).
3. Run the relevant test suite before opening a pull request.
4. Follow the existing code style; run any provided linters/formatters.

## Pull request process

1. Open an issue or link to an existing one describing the motivation.
2. Keep pull requests focused — one logical change per PR.
3. Include tests for new behavior and update relevant docs in the same PR.
4. Fill out the pull request template completely.
5. A maintainer will review, request changes if needed, and merge once approved and CI passes.

## Commit messages

Use clear, imperative commit messages (e.g., "Add retry logic to browser executor" rather than "fixed stuff"). Reference the related issue number where applicable.

## Code review expectations

Reviews focus on correctness, clarity, security implications (especially around browser execution and credential handling), and alignment with the outcome-first product philosophy described in [docs/vision.md](docs/vision.md).

## Reporting security issues

Do not open a public issue for security vulnerabilities. Follow the process in [SECURITY.md](SECURITY.md).

## Code of Conduct

All contributors are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).
