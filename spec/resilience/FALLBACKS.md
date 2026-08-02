# Fallbacks

| Primary path fails | Fallback |
|---|---|
| Preferred source unreachable | Next-ranked candidate source from Router's selection |
| Browser session fails/circuit-broken | Static fetch with reduced extraction confidence, flagged accordingly |
| Graph query layer unavailable | Synthesis proceeds without graph context (degrades relationship-awareness, doesn't fail the run) |
| Memory store unavailable | Treat every fetch as fresh (no reuse) rather than failing — see [../resilience/FAILURE_MODES.md](../resilience/FAILURE_MODES.md) and [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) |
| Skill match fails | Planner falls back to freeform task classification and planning |
| Custom ranker override fails to evaluate | Fall back to default [Ranking](../module-specs/RANKING_SPEC.md) behavior, log the override failure |

Fallbacks should always be reflected in the execution trace so degraded results are inspectable, not silently indistinguishable from a full-quality run.
