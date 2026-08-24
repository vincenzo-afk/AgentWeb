# Monitoring

Implements ongoing observation of pages, entities, product listings, policy pages, docs, releases, or mentions, producing alerts or triggering downstream workflows on change.

## Lifecycle

1. A monitor is created via [`/observe`](../api/reference/monitor.md) with a task description, optional frequency, and optional change policy.
2. The scheduler runs periodic checks against the target, using [Memory](memory.md) to store an immutable, tenant-scoped snapshot and content hash.
3. The parser produces a bounded projection containing `title`, `text`, `links`, `tables`, `entities`, and JSON `data` when available.
4. The comparison engine evaluates the new snapshot against the latest one. A `structured_field` policy can traverse a bounded dotted path such as `data.price` or `tables.0.1.1`.
5. If a meaningful change is detected according to the policy, an alert is delivered via [webhook](../api/webhooks.md) or made available through polling.

## Structured-field policies

Structured-field monitoring is deterministic and local-first. It does not implement arbitrary JSONPath, browser-only DOM state, or managed extraction infrastructure. A policy names one field and an expected type:

```json
{
  "kind": "structured_field",
  "field_path": "data.price",
  "expected_type": "price",
  "absolute_delta": 5,
  "ignore_whitespace": true
}
```

The path is bounded to the parser projection and supports dictionary keys plus numeric list indexes. `string` values can ignore whitespace; `entity`, `price`, and `date` values use the deterministic locale-aware normalizer. Price fields may use absolute and/or relative thresholds. Missing fields are stable when absent in both snapshots, while either presence transition is meaningful.

The projection is persisted with the snapshot only as an internal comparison input. The established snapshot listing and content diff interfaces remain unchanged, and no credentials or signing secrets are persisted in the projection. A fetch or trust failure records `check_failed`, never a successful `no_change` result.

## Frequency and cost

Check frequency (`minutely`, `hourly`, `daily`) trades off responsiveness against cost; see [operations/cost-controls.md](../operations/cost-controls.md). SQLite remains the default persistence layer for this local MVP; optional PostgreSQL coordination does not imply a full business-record runtime cutover.

## Relationship to the event-driven model

Monitoring is the current building block toward the longer-term [event-driven internet model](../concepts/event-driven-internet.md), where detected changes eventually trigger richer downstream workflows automatically rather than only delivering an alert.
