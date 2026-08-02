# Configuration

## Configuration sources (precedence, highest first)

1. Per-request overrides (e.g., `mode`, `ranker_overrides` in the request body)
2. Organization-level settings (e.g., default mode restrictions, monitor frequency caps — see [../../docs/operations/cost-controls.md](../../docs/operations/cost-controls.md))
3. Environment configuration (see [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md))
4. System defaults (see [DEFAULTS.md](DEFAULTS.md))

## Principles
- No secret values in configuration files committed to source control — see [../../docs/security/secrets-management.md](../../docs/security/secrets-management.md).
- Configuration changes affecting cost or safety behavior (e.g., raising a rate limit, disabling a Trust Engine gate) should be auditable — see [../observability/AUDITING.md](../observability/AUDITING.md).
