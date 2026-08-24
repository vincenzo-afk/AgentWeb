# Monitor Module Specification

## Purpose

Recurring, scheduled observation with deterministic change detection. See [docs/core/monitoring.md](../../docs/core/monitoring.md) and [docs/api/reference/monitor.md](../../docs/api/reference/monitor.md).

## Interface

```text
create_monitor(task: string, frequency?: string, webhook_url?: string, change_policy?: object) -> Monitor
check_monitor(monitor_id: string) -> CheckResult
```

## Behavior

1. The scheduler triggers a check according to `frequency`.
2. The router fetches the current target state after applying trust and URL-safety policy.
3. [Memory](MEMORY_SPEC.md) stores an immutable, organization-scoped content version and hash. For a successful parse, the monitor also stores a bounded parser projection containing `title`, `text`, `links`, `tables`, `entities`, and JSON `data`.
4. On meaningful change, [Alerting](ALERTING_SPEC.md) is triggered. Without an explicit policy, task-aware full-content, price, or availability comparison is used.
5. A `structured_field` policy has the form `{kind, field_path, expected_type, ignore_whitespace?, absolute_delta?, relative_delta_percent?}`. `field_path` is a bounded dotted path over the parser projection, with named object keys and numeric list indexes; it is not arbitrary JSONPath or browser-only state.
6. `expected_type` is `string`, `entity`, `price`, or `date`. The normalizer canonicalizes recognized entity, price, and date values deterministically; unparseable values remain raw. Price thresholds are valid only for `expected_type: price` and fire when the absolute or relative delta meets the configured threshold.
7. A structured field absent in both snapshots is not a change. Missing-to-present and present-to-missing transitions are meaningful changes. Irrelevant changes outside the selected field do not trigger a structured-field alert.
8. Snapshot and monitor records remain organization-scoped. Structured projection data is an internal comparison input; existing snapshot list and diff response shapes remain unchanged.

## Failure modes

A target unreachable at check time, rejected by trust policy, or otherwise failing the fetch boundary produces a `check_failed` event and is retried on the next scheduled tick. It must never be treated as a `no_change` result, avoiding false negatives. See [../resilience/RETRY_POLICY.md](../resilience/RETRY_POLICY.md).
