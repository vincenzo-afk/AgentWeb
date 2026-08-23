# Contributing to AgentWeb

Thank you for improving AgentWeb. The repository now contains a small Python 3.11+ MVP as well as the broader product and module specifications. Keep changes focused, evidence-based, and consistent with the boundary between implemented behavior and future roadmap work.

## Before you start

For a bug, use the [bug report form](.github/ISSUE_TEMPLATE/bug_report.yml). For a new capability, use the [feature request form](.github/ISSUE_TEMPLATE/feature_request.yml) and explain the smallest useful scope. Do not include API keys, cookies, private page contents, or local SQLite databases in issues or pull requests.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable .
python -m compileall -q src tests
PYTHONPATH=src python -m unittest discover -s tests -v
```

The runtime has no third-party dependencies. The test suite uses local HTTP fixtures and should not require paid services or internet access. If you add a dependency, explain why the Python standard library is insufficient and update `pyproject.toml` and the README.

## Pull requests

Use a focused branch with a descriptive name, keep one logical change per pull request, and complete the [pull-request template](.github/pull_request_template.md). Public API changes must update `openapi/openapi.yaml`, relevant schemas or docs, tests, and the README when the user workflow changes. CI must pass before merge.

## Code expectations

Prefer small standard-library components, explicit validation, deterministic tests, and clear error responses. Network-facing code must bound response sizes and timeouts, validate URLs, and avoid logging secrets. Treat fetched web content as untrusted data. Do not claim roadmap modules are implemented unless the code and tests support the claim.

Use clear, imperative commit messages. Reviewers will consider correctness, maintainability, test coverage, documentation accuracy, security implications, and compatibility with the documented API.

## Code of Conduct and security

All contributors must follow the [Code of Conduct](CODE_OF_CONDUCT.md). Do not open a public issue for a vulnerability; follow [SECURITY.md](SECURITY.md) instead.
