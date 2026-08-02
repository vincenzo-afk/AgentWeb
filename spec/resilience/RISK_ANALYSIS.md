# Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Third-party site blocks AgentWeb traffic at scale | Medium | Medium | Per-domain rate limiting + circuit breakers ([CIRCUIT_BREAKERS.md](CIRCUIT_BREAKERS.md)); respectful crawling behavior ([../module-specs/TRUST_ENGINE_SPEC.md](../module-specs/TRUST_ENGINE_SPEC.md)) |
| Trust scoring miscalibrated for a niche domain, producing misleading citations | Medium | High | Per-domain ranker overrides ([../../docs/guides/source-trust-tuning.md](../../docs/guides/source-trust-tuning.md)); explicit uncertainty surfacing in Synthesis |
| Browser sandbox escape / malicious page exploit | Low | High | Strict sandboxing ([../../docs/security/sandboxing.md](../../docs/security/sandboxing.md)); network egress restriction ([../architecture/NETWORK_ARCHITECTURE.md](../architecture/NETWORK_ARCHITECTURE.md)) |
| Runaway monitor cost from high-frequency, high-volume monitors | Medium | Medium | Frequency tier caps, usage alerts ([../../docs/operations/cost-controls.md](../../docs/operations/cost-controls.md)) |
| Data privacy exposure via shared graph intelligence | Low | High | Organizational isolation by default, explicit opt-in for shared graph contribution ([../../docs/security/data-privacy.md](../../docs/security/data-privacy.md)) |
| Webhook signing secret leaked, enabling forged alerts | Low | Medium | Secret rotation support, signature + timestamp verification requirement ([../api/WEBHOOKS.md](../api/WEBHOOKS.md)) |

See [../security/SECURITY_MODEL.md](../security/SECURITY_MODEL.md) for the broader threat model these risks sit within.
