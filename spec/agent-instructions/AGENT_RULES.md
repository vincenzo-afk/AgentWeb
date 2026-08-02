# Agent Rules

Hard constraints for any agent implementing or modifying this system:

1. **Never violate an [invariant](../decisions/INVARIANTS.md).** If a task seems to require violating one, stop and flag it rather than proceeding.
2. **Never implement a module's behavior in a way that contradicts its `*_SPEC.md`.** If implementation reveals the spec is wrong or incomplete, update the spec in the same change — don't let code and spec diverge silently.
3. **Never skip [DONE_DEFINITION.md](../testing/DONE_DEFINITION.md) requirements** to move faster, including test coverage and observability instrumentation for new failure-capable code paths.
4. **Never introduce a dependency that violates [MODULE_DEPENDENCIES.md](../build-plan/MODULE_DEPENDENCIES.md)** (e.g., Memory depending on Graph) without first updating the architecture docs and getting the change reviewed — dependency direction is a deliberate design choice, not incidental.
5. **Never log or persist secret values**, per [../decisions/INVARIANTS.md](../decisions/INVARIANTS.md) item 6.
6. **Never expand scope beyond [PROJECT_SCOPE.md](../product/PROJECT_SCOPE.md)/[NON_GOALS.md](../product/NON_GOALS.md)** without an explicit human decision recorded in [DECISION_HISTORY.md](DECISION_HISTORY.md).
7. **When uncertain, prefer the documented fallback/degradation behavior** ([../resilience/FALLBACKS.md](../resilience/FALLBACKS.md)) over inventing new failure handling ad hoc.
