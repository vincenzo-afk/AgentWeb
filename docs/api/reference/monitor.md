# `POST /observe`

Creates a recurring monitor: AgentWeb periodically checks a target, uses the memory layer to detect change, and delivers alerts via webhook (or lets you poll status).

## Request

```json
{
  "task": "Track visa slot availability and alert when a new slot appears",
  "webhook_url": "https://myapp.example.com/webhooks/agentweb",
  "frequency": "hourly"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `task` | string | yes | What to watch and what counts as a change worth alerting on |
| `webhook_url` | string | no | Delivery target for change alerts; see [webhooks.md](../webhooks.md) |
| `frequency` | string | no | `minutely`, `hourly`, `daily` (defaults based on task type) |

## `GET /observe/{id}`

Returns monitor status and history:

```json
{
  "id": "mon_abc123",
  "status": "active",
  "last_checked_at": "2026-07-31T12:00:00Z",
  "last_change_at": "2026-07-29T08:00:00Z"
}
```

## `DELETE /observe/{id}`

Cancels the monitor.

See [core/monitoring.md](../../core/monitoring.md) and [guides/building-monitors.md](../../guides/building-monitors.md).
