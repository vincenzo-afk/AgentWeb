# Coding Standards

- Every module in [../module-specs/](../module-specs/) implements the interface documented in its spec exactly — signature drift between spec and implementation must be reflected back into the spec in the same change.
- All external I/O (fetching a URL, calling a store) goes through an explicit adapter/interface, never inline, so it can be mocked in [../testing/UNIT_TESTS.md](../testing/UNIT_TESTS.md).
- Errors are typed/structured (matching [../api/ERROR_CODES.md](../api/ERROR_CODES.md) categories internally too), not raw strings.
- No secret values, ever, in code, logs, or committed configuration — see [../../docs/security/secrets-management.md](../../docs/security/secrets-management.md).
- Every publicly exposed function/endpoint requires a docstring/comment describing inputs, outputs, and failure modes, consistent with [DOCUMENTATION_STANDARDS.md](DOCUMENTATION_STANDARDS.md).

See [STYLE_GUIDE.md](STYLE_GUIDE.md) for formatting/lint specifics and [CODE_STRUCTURE.md](CODE_STRUCTURE.md) for repository layout conventions.
