# Enterprise Rollout

Considerations for rolling out AgentWeb in production, compliance-sensitive environments.

## Evaluation checklist

- **Explainability** — confirm execution graphs and citations meet your audit requirements ([concepts/explainability.md](../concepts/explainability.md)).
- **Data handling** — review [security/data-privacy.md](../security/data-privacy.md) for how third-party page content is stored/retained.
- **Access control** — use scoped API keys per team/use case ([api/authentication.md](../api/authentication.md)).
- **Cost governance** — set usage alerts and mode restrictions ([operations/cost-controls.md](../operations/cost-controls.md)).
- **Reliability** — review [operations/sla-slo.md](../operations/sla-slo.md) and [operations/disaster-recovery.md](../operations/disaster-recovery.md).

## Phased rollout

1. Pilot with a single low-risk workflow (e.g., internal research assistant) using test keys.
2. Expand to production with scoped keys and usage monitoring.
3. Enable monitors for recurring workflows once trust in output quality is established.
4. Formalize an internal review process for any customer-facing use of synthesized output, particularly where citations drive decisions.
