# Agent Workflow

## Standard loop for implementing a module

1. Read the module's `*_SPEC.md` in [../module-specs/](../module-specs/) fully before writing code.
2. Check [../build-plan/MODULE_DEPENDENCIES.md](../build-plan/MODULE_DEPENDENCIES.md) — confirm all hard dependencies are already implemented and passing their own [acceptance criteria](../testing/ACCEPTANCE_CRITERIA.md).
3. Implement the interface exactly as specified; if a deviation is needed, update the spec file in the same change and note why in [DECISION_HISTORY.md](DECISION_HISTORY.md).
4. Write unit tests covering the happy path, every documented failure mode, and any relevant [edge cases](../resilience/EDGE_CASES.md).
5. Add observability (logging/metrics/tracing) per [../observability/](../observability/) conventions for any new failure-capable code path.
6. Run the [Definition of Done](../testing/DONE_DEFINITION.md) checklist before considering the task complete.
7. Update [PROJECT_MEMORY.md](PROJECT_MEMORY.md) with anything a future agent/session would need to know to avoid re-deriving context.

## When picking up an existing in-progress task
Read [PROJECT_MEMORY.md](PROJECT_MEMORY.md) and [DECISION_HISTORY.md](DECISION_HISTORY.md) first — don't re-litigate settled decisions without new information.
