# Quality Gates

## CI gates (block merge)
- Unit + integration tests pass
- Linting/formatting checks pass ([../standards/STYLE_GUIDE.md](../standards/STYLE_GUIDE.md))
- OpenAPI spec validates ([openapi/openapi.yaml](../../openapi/openapi.yaml))
- No new secret-looking strings detected in diff (basic secret-scanning)

## Release gates (block deploy)
- System + E2E tests pass against staging
- No open severity-1 bugs (including any [invariant](../decisions/INVARIANTS.md) violation)
- [Benchmarks](BENCHMARKS.md) show no regression beyond an agreed threshold vs. the previous release
- Security review sign-off for any change touching browser execution, credential handling, or data storage/retention

## Milestone gates
See [../build-plan/MILESTONES.md](../build-plan/MILESTONES.md) — a milestone cannot be marked complete until its exit criteria and the standard release gates above both pass.
