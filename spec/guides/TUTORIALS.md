# Tutorials

Build-oriented, step-by-step tutorials for implementers (distinct from [docs/getting-started/](../../docs/getting-started/index.md), which is usage-oriented for API consumers).

## Tutorial: implementing a new execution primitive
1. Write the `*_SPEC.md` in [../module-specs/](../module-specs/) first, following the existing spec format.
2. Add the module to [../architecture/MODULES.md](../architecture/MODULES.md) and [../architecture/DEPENDENCY_GRAPH.md](../architecture/DEPENDENCY_GRAPH.md).
3. Implement per [../standards/CODING_STANDARDS.md](../standards/CODING_STANDARDS.md).
4. Add unit + integration tests per [../testing/](../testing/).
5. Add observability per [../observability/](../observability/).
6. Update [../build-plan/BUILD_ORDER.md](../build-plan/BUILD_ORDER.md) if this introduces new dependencies.

## Tutorial: adding a new Connector
See [docs/guides/building-connectors.md](../../docs/guides/building-connectors.md) for the usage-facing version; the interface contract is in [../module-specs/CONNECTOR_SPEC.md](../module-specs/CONNECTOR_SPEC.md).

## Tutorial: adding a new Skill
See [docs/guides/creating-skills.md](../../docs/guides/creating-skills.md) and [../module-specs/SKILLS_SPEC.md](../module-specs/SKILLS_SPEC.md).
