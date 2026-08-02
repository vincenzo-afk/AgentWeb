# Failure Modes

| Failure | Detection | Response |
|---|---|---|
| Target site unreachable | Connection timeout/error on fetch | Retry per [RETRY_POLICY.md](RETRY_POLICY.md); exclude source if exhausted, continue run |
| Target site rate-limits/blocks AgentWeb | 403/429 from target | Back off per-domain; try alternate source via [FALLBACKS.md](FALLBACKS.md) |
| Browser session crash/hang | Timeout or process exit | Kill session, retry once per [TIMEOUT_POLICY.md](TIMEOUT_POLICY.md), then fail that step only |
| Extraction produces low-confidence data | Confidence score below threshold | Down-weight in ranking rather than discard; flag for synthesis uncertainty handling |
| Memory store unavailable | Store health check / write failure | Degrade to no-reuse mode (treat every fetch as fresh) rather than failing the run — see [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) |
| Webhook receiver down | Non-2xx / timeout on delivery | Retry per [RETRY_POLICY.md](RETRY_POLICY.md); surface via monitor status after exhaustion |
| Conflicting evidence across sources | Ranking/Synthesis disagreement detection | Surface disagreement explicitly in the answer, not silently resolved |

See [RISK_ANALYSIS.md](RISK_ANALYSIS.md) for likelihood/impact assessment of each.
