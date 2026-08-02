# Compliance Notes

AgentWeb is early-stage; this page tracks compliance-relevant considerations rather than asserting formal certifications.

## Considerations for regulated use cases

- **Auditability** — [execution graphs](../concepts/execution-graphs.md) provide a replayable evidence trail, which is useful but should be evaluated against your specific regulatory framework's requirements before relying on it as a compliance artifact.
- **Data residency** — confirm current storage region options with your account team before use in jurisdictions with data residency requirements.
- **Retention alignment** — default retention windows are described in [operations/data-retention.md](../operations/data-retention.md); longer retention may be available for audit needs.
- **Source reliability disclosure** — [trust scores](../concepts/trust-model.md) and citations should be treated as decision-support signals, not a substitute for your own verification process in high-stakes compliance contexts.

## Recommendation

Treat this page as a starting point for your own compliance review, not a substitute for it. See [guides/enterprise-rollout.md](../guides/enterprise-rollout.md) for a broader rollout checklist.
