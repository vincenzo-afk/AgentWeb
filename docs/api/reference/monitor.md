# `POST /observe`

Creates a recurring monitor: AgentWeb periodically checks a target, uses the memory layer to detect change, and delivers alerts via webhook (or lets you poll status).

## Request

```json
{
  "task": "Track visa slot availability and alert when a new slot appears",
  "webhook_url": "https://myapp.example.com/webhooks/agentweb",
  "frequency": "hourly",
  "change_policy": {
    "kind": "availability",
    "required_state": "available"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `task` | string | yes | What to watch and what counts as a change worth alerting on |
| `webhook_url` | string | no | Delivery target for change alerts; see [webhooks.md](../webhooks.md) |
| `frequency` | string | no | `minutely`, `hourly`, `daily` (defaults based on task type) |
| `change_policy` | object | no | Optional deterministic policy using `kind`, `absolute_delta`, `relative_delta_percent`, `required_state`, and `ignore_whitespace` |

## `GET /observe/{id}`

Returns monitor status and history. When a change webhook is configured, delivery is queued as a tenant-owned `webhook_delivery` job. Polling exposes the latest delivery state without exposing the signing secret. States include `pending`, `retrying`, `rate_limited`, `delivered`, `dead_letter`, and `blocked`.

Returns monitor status and history:

```json
{
  "id": "mon_abc123",
  "status": "active",
  "last_checked_at": "2026-07-31T12:00:00Z",
  "last_change_at": "2026-07-29T08:00:00Z",
  "last_delivery_id": "job_abc123",
  "last_delivery_status": "delivered",
  "last_delivery_attempts": 1,
  "last_delivery_error": ""
}
```

## `DELETE /observe/{id}`

Cancels the monitor. Any pending monitor-check and webhook-delivery jobs owned by the organization are no longer eligible for execution.

See [core/monitoring.md](../../core/monitoring.md) and [guides/building-monitors.md](../../guides/building-monitors.md).
