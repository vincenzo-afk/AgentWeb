# `POST /solve`

The primary outcome-first endpoint. Describe a task; AgentWeb plans and executes the necessary search, browsing, extraction, and synthesis, returning a grounded, cited answer.

## Request

```json
{
  "task": "Find the cheapest RTX 6090 currently available in India and cite trustworthy sources",
  "mode": "dive",
  "webhook_url": "https://myapp.example.com/webhooks/agentweb",
  "idempotency_key": "optional-client-uuid"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `task` | string | yes | Natural-language intent |
| `mode` | string | no | `flash`, `focus`, `dive` (planner chooses if omitted) |
| `skill` | string | no | Use a named [Internet Skill](../../concepts/internet-skills.md) instead of freeform planning |
| `webhook_url` | string | no | Callback for async delivery on long `dive` runs |
| `idempotency_key` | string | no | See [idempotency.md](../idempotency.md) |

## Response

See [responses.md](../responses.md) and [citations.md](../citations.md) for the full answer/sources/citations shape.
