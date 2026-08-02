# Compliance

See [docs/security/compliance-notes.md](../../docs/security/compliance-notes.md) for the customer-facing compliance considerations page. Build-level notes:

- Execution traces ([../architecture/EXECUTION_GRAPH.md](../architecture/EXECUTION_GRAPH.md)) are designed to support audit use cases but are not themselves a certified compliance artifact — treat them as evidence infrastructure, not a substitute for a compliance program.
- Data residency requirements, if committed to for a given deployment, must be reflected in [../data/STORAGE_SPEC.md](../data/STORAGE_SPEC.md) region configuration, not assumed.
- Retention windows in [../config/DEFAULTS.md](../config/DEFAULTS.md) should be reviewed against any specific regulatory retention requirement before being treated as compliant defaults for a given customer's jurisdiction.
