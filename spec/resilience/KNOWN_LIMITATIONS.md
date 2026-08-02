# Known Limitations

- **No graph reasoning until Phase 2.** Relationship-heavy queries are answered via freeform synthesis (weaker) until [../module-specs/GRAPH_SPEC.md](../module-specs/GRAPH_SPEC.md) reaches GA.
- **Trust scoring is not domain-certified.** `trust_score` is a relative reliability signal, not a compliance or legal certification — see [../../docs/security/compliance-notes.md](../../docs/security/compliance-notes.md).
- **Browser workflows requiring CAPTCHA-solving or multi-factor authentication are not supported** — these require human-in-the-loop interaction outside AgentWeb's automation model.
- **Memory reuse has an inherent staleness tradeoff.** Even with task-aware freshness windows, monitoring cannot guarantee zero-latency detection of a change — see [TIMEOUT_POLICY.md](TIMEOUT_POLICY.md) and [../module-specs/MONITOR_SPEC.md](../module-specs/MONITOR_SPEC.md) for the achievable frequency tiers.
- **Non-English and low-resource-language content extraction quality may lag English** in the current Extractor/Normalizer implementation.
- **Graceful degradation, not elimination, of third-party unreliability.** No amount of retry/fallback logic can guarantee availability of content AgentWeb doesn't control.
