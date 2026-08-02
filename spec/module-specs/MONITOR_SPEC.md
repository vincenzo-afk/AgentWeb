# Monitor Spec

## Purpose
Recurring, scheduled observation with change detection. See [docs/core/monitoring.md](../../docs/core/monitoring.md) and [docs/api/reference/monitor.md](../../docs/api/reference/monitor.md).

## Interface
```
create_monitor(task: string, frequency?: string, webhook_url?: string) -> Monitor
check_monitor(monitor_id: string) -> CheckResult
```

## Behavior
1. Scheduler triggers a check per `frequency`.
2. Router fetches current target state.
3. [Memory](MEMORY_SPEC.md) hashes and compares to last snapshot.
4. On meaningful change (task-specific criteria), [Alerting](ALERTING_SPEC.md) is triggered.

## Failure modes
Target unreachable at check time → record a `check_failed` event, retry next scheduled tick; do not treat as a "no change" result (avoid false negatives). See [../resilience/RETRY_POLICY.md](../resilience/RETRY_POLICY.md).
