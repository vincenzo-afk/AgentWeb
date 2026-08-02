# Troubleshooting

Build/implementation-time troubleshooting (distinct from [docs/getting-started/debugging-basics.md](../../docs/getting-started/debugging-basics.md), which is for API consumers debugging their own requests).

| Symptom | Likely cause | Check |
|---|---|---|
| Unit tests pass but integration tests fail | Mocked adapter behavior doesn't match real store behavior | [../testing/INTEGRATION_TESTS.md](../testing/INTEGRATION_TESTS.md) fixtures vs. real store schema |
| A module's behavior diverges from its spec | Spec and implementation drifted | Re-sync per [../standards/CODING_STANDARDS.md](../standards/CODING_STANDARDS.md) rule 1 |
| Circular dependency error at build time | New module violates [MODULE_DEPENDENCIES.md](../build-plan/MODULE_DEPENDENCIES.md) | Re-check [../architecture/DEPENDENCY_GRAPH.md](../architecture/DEPENDENCY_GRAPH.md) before adding the dependency |
| Execution trace missing expected spans | New code path added without [tracing](../observability/TRACING.md) instrumentation | Add spans per [DONE_DEFINITION.md](../testing/DONE_DEFINITION.md) observability requirement |
| Invariant violated in a new code path | Missed [../decisions/INVARIANTS.md](../decisions/INVARIANTS.md) check during review | Add explicit test per [../testing/ACCEPTANCE_CRITERIA.md](../testing/ACCEPTANCE_CRITERIA.md) |

If the issue isn't listed here, log it via [../agent-instructions/PROJECT_MEMORY.md](../agent-instructions/PROJECT_MEMORY.md) once resolved so it's captured for next time.
