# `POST /observe`

Creates a recurring monitor. AgentWeb periodically fetches a target, parses the response, stores an immutable tenant-scoped snapshot, and evaluates an optional deterministic change policy. Changes can be delivered through an explicitly configured webhook or observed by polling monitor status.

## Request

```json
{
  "task": "Track the product price in the first table cell",
  "webhook_url": "https://myapp.example.com/webhooks/agentweb",
  "frequency": "hourly",
  "change_policy": {
    "kind": "structured_field",
    "field_path": "tables.0.1.1",
    "expected_type": "price",
    "absolute_delta": 5,
    "relative_delta_percent": 10,
    "ignore_whitespace": true
  }
}
```

| Field | Type | Required | Description |
|---|---|---:|---|
| `task` | string | yes | What to watch and what counts as a meaningful change. The task must contain a directly fetchable URL. |
| `webhook_url` | string | no | Delivery target for change alerts; see [webhooks.md](../webhooks.md). |
| `frequency` | string | no | `minutely`, `hourly`, or `daily`; defaults are selected from the task type. |
| `change_policy` | object | no | Optional deterministic policy using the fields below. |

## Change policies

The existing policy kinds are `full_content`, `price`, and `availability`. A structured policy adds field-level comparison over the parser projection:

```json
{
  "kind": "structured_field",
  "field_path": "data.price",
  "expected_type": "price",
  "absolute_delta": 5
}
```

`field_path` is a bounded dotted object/list path, not arbitrary JSONPath. It may traverse the fixed projection roots `title`, `text`, `links`, `tables`, `entities`, and `data`; object segments use names such as `data.price`, while list segments use decimal indexes such as `tables.0.1.1`. The path grammar accepts identifiers with letters, digits, underscores, and hyphens, plus numeric list indexes. Out-of-range indexes and absent object keys are treated as missing fields.

| Policy field | Type | Applies to | Behavior |
|---|---|---|---|
| `kind` | string | all policies | `structured_field` enables parsed field comparison. |
| `field_path` | string | `structured_field` | Required bounded dotted path into the parsed projection. |
| `expected_type` | string | `structured_field` | `string`, `entity`, `price`, or `date`; defaults to `string`. |
| `absolute_delta` | number, ≥ 0 | price policies | For structured prices, reports a change when the absolute numeric delta is at least this value. |
| `relative_delta_percent` | number, 0–10000 | price policies | For structured prices, reports a change when the relative delta is at least this percentage. |
| `required_state` | string | `availability` | Supported states are `in stock`, `out of stock`, `available`, `unavailable`, and `sold out`; it is not valid for structured fields. |
| `ignore_whitespace` | boolean | content/string policies | Collapses runs of whitespace and trims string values before comparison. |

Structured `price` values use the locale-aware deterministic normalizer and compare numeric values when parsing succeeds. `date` values are canonicalized to an ISO date when recognized, and `entity` values use normalized whitespace and case-insensitive comparison behavior from the normalizer. Unparseable values remain raw and are compared deterministically. Numeric thresholds are accepted only with `expected_type: "price"`; a threshold of zero still requires a non-zero delta. If the field is absent in both snapshots, the result is `no_change`. A missing-to-present or present-to-missing transition is a meaningful `change_detected` event.

The parsed projection is stored with the immutable snapshot for monitor comparison. The existing snapshot list and diff response continue to expose their established content/hash fields; structured projection data is an internal comparison input and is not an unrestricted API data-export surface.

## `GET /observe/{id}`

Returns monitor status and history. When a change webhook is configured, delivery is queued as a tenant-owned `webhook_delivery` job. Polling exposes the latest delivery state without exposing the signing secret. States include `pending`, `retrying`, `rate_limited`, `delivered`, `dead_letter`, and `blocked`.

```json
{
  "id": "mon_abc123",
  "status": "active",
  "change_policy": {
    "kind": "structured_field",
    "field_path": "data.price",
    "expected_type": "price"
  },
  "last_checked_at": "2026-07-31T12:00:00Z",
  "last_change_at": "2026-07-29T08:00:00Z",
  "last_delivery_id": "job_abc123",
  "last_delivery_status": "delivered",
  "last_delivery_attempts": 1,
  "last_delivery_error": ""
}
```

A fetch, trust, or parse boundary failure records `check_failed`; it is never treated as `no_change`.

## `DELETE /observe/{id}`

Cancels the monitor. Any pending monitor-check and webhook-delivery jobs owned by the organization are no longer eligible for execution.

See [core/monitoring.md](../../core/monitoring.md) and [guides/building-monitors.md](../../guides/building-monitors.md).
