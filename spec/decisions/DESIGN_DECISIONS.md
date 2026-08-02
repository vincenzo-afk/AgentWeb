# Design Decisions

Lower-level, module-specific decisions that don't rise to full ADR status in [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md).

- **Synthesis surfaces disagreement rather than picking a winner** when sources conflict — preserves trust over apparent confidence (see [../module-specs/SYNTHESIS_SPEC.md](../module-specs/SYNTHESIS_SPEC.md)).
- **Router prefers static fetch over Browser by default** — cost/latency optimization; Browser is an escalation, not the default path (see [../module-specs/BROWSER_SPEC.md](../module-specs/BROWSER_SPEC.md)).
- **Extraction confidence is a first-class field**, not just a pass/fail — allows Ranking to weight low-confidence extractions down rather than excluding them outright.
- **Monitor "no change" and "check failed" are distinct states** — avoids false negatives where an unreachable target is silently treated as unchanged (see [../module-specs/MONITOR_SPEC.md](../module-specs/MONITOR_SPEC.md)).
