# Secrets Management

See [docs/security/secrets-management.md](../../docs/security/secrets-management.md) for customer-facing guidance. Build-level requirements:

- Platform secrets (`DATABASE_URL`, `WEBHOOK_SIGNING_KEY`, etc. — see [../config/ENVIRONMENT_VARIABLES.md](../config/ENVIRONMENT_VARIABLES.md)) are sourced from a secrets manager in every non-local environment, never committed to source control.
- Customer API keys are stored hashed, never in plaintext, per [../data/DATABASE_SCHEMA.md](../data/DATABASE_SCHEMA.md).
- Any credential a customer supplies for authenticated browser workflows ([../module-specs/BROWSER_SPEC.md](../module-specs/BROWSER_SPEC.md)) is encrypted at rest and never written to execution traces or logs — enforced as [../decisions/INVARIANTS.md](../decisions/INVARIANTS.md) item 6.
