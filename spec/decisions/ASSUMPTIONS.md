# Assumptions

- Most target pages are publicly accessible without authentication; authenticated-flow browsing ([../module-specs/BROWSER_SPEC.md](../module-specs/BROWSER_SPEC.md) interaction scripts) is a supported but secondary path, not the default assumption.
- Task descriptions are provided in natural language and are generally well-formed; extremely malformed or adversarial task text is handled defensively (see [../resilience/EDGE_CASES.md](../resilience/EDGE_CASES.md)) but not specially optimized for.
- Customers calling the API are backend services, not browsers — client-side key exposure is treated as a misuse case to guard against ([../../docs/security/secrets-management.md](../../docs/security/secrets-management.md)), not a first-class supported pattern.
- Source reliability is domain-dependent and cannot be fully generalized by a single global trust score — this is why per-domain overrides exist ([../../docs/guides/source-trust-tuning.md](../../docs/guides/source-trust-tuning.md)).
- Recurring monitors dominate cost at scale more than one-shot `solve` calls, which is why memory reuse and monitor frequency tiers receive disproportionate optimization attention (see [CONSTRAINTS.md](CONSTRAINTS.md)).
