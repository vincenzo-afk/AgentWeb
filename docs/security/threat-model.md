# Threat Model

## Key risk areas, given AgentWeb's architecture

- **Arbitrary third-party page execution** — the [browser layer](../core/browser-engine.md) renders and executes JS from sites AgentWeb doesn't control. Mitigated via [sandboxing](sandboxing.md).
- **Malicious or adversarial pages** — pages designed to poison extraction, trigger excessive resource use, or exploit the browser engine itself. Mitigated via resource limits, sandbox isolation, and [Trust and Safety](../core/trust-and-safety.md) filtering.
- **Credential/API key leakage** — since AgentWeb is typically called from backend services, key exposure risk centers on client-side misuse or logging. See [secrets-management.md](secrets-management.md).
- **Webhook spoofing/replay** — a third party sending forged monitor-alert payloads. Mitigated via signed payloads; see [api/webhooks.md](../api/webhooks.md).
- **Data leakage across organizations** — snapshot/graph data must remain scoped to the owning organization even as graph intelligence potentially benefits from cross-source corroboration. See [data-privacy.md](data-privacy.md).
- **Abuse for scraping/DoS against third-party sites** — AgentWeb's own infrastructure could be used to overload a target site. Mitigated via per-target rate limiting in [Trust and Safety](../core/trust-and-safety.md).

## Out of scope

AgentWeb's threat model covers the platform's own infrastructure and data handling. It does not warrant the security posture of third-party sites it browses/extracts from.
