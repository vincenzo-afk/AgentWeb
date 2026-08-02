# Definition of Done

A task/feature is "done" only when all of the following hold:

- [ ] Implementation matches its spec in [../module-specs/](../module-specs/) or [../api/](../api/) exactly (or the spec was updated in the same change to match a deliberate deviation)
- [ ] Unit tests pass ([UNIT_TESTS.md](UNIT_TESTS.md))
- [ ] Relevant integration/system tests pass ([INTEGRATION_TESTS.md](INTEGRATION_TESTS.md), [SYSTEM_TESTS.md](SYSTEM_TESTS.md))
- [ ] No new violation of any [invariant](../decisions/INVARIANTS.md)
- [ ] Relevant `docs/` prose documentation updated if user-facing behavior changed
- [ ] Observability (logging/metrics/tracing) added per [../observability/](../observability/) conventions for anything new that can fail
- [ ] Security review completed for anything touching [../security/SECURITY_MODEL.md](../security/SECURITY_MODEL.md) risk areas (browser execution, credentials, data storage)

See [QUALITY_GATES.md](QUALITY_GATES.md) for how this is enforced in CI/release process.
