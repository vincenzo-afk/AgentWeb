# Explainability

Explainability is a core requirement, not an add-on. AgentWeb should not only return an answer — it should show the evidence path: which sources were used, why those sources were selected, what browser actions occurred, what changed between snapshots, and why a trust score is high or low.

This matters because grounded internet workflows are often used for decisions, monitoring, research, or compliance-sensitive tasks, where users need to inspect the basis of a result rather than accept a black-box output.

In practice, explainability is delivered through:

- **Citations** on every synthesized claim (see [api/citations.md](../api/citations.md))
- **Execution graphs** recording the full plan and actions for a run (see [Execution Graphs](execution-graphs.md))
- **Trust scores** exposed per source (see [Trust Model](trust-model.md))
- **Diffs** showing exactly what changed between snapshots for monitored targets

Enterprise and compliance-sensitive users should treat this as a first-class evaluation criterion — see [guides/enterprise-rollout.md](../guides/enterprise-rollout.md).
