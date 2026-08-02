# Event Flow

## Monitor / async event path

```
Scheduler tick
   → Monitor: fetch target via Router
   → Memory: hash + compare to last snapshot
   → [no change] → update last_checked_at, stop
   → [change detected] → Memory: store new snapshot, compute diff
   → Alerting: build payload, sign, deliver webhook
   → Graph: update relevant entities (if applicable)
   → Observability: record event in execution trace
```

This is the current building block toward the full [event-driven internet model](../../docs/concepts/event-driven-internet.md). See [../module-specs/MONITOR_SPEC.md](../module-specs/MONITOR_SPEC.md) and [../module-specs/ALERTING_SPEC.md](../module-specs/ALERTING_SPEC.md) for module-level detail.
