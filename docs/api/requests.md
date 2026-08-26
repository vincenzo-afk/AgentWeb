# Requests

All requests are JSON over HTTPS with `Content-Type: application/json`.

## Common fields

| Field | Type | Description |
|---|---|---|
| `task` | string | Natural-language description of intent for `solve` or `/observe` |
| `mode` | string | Optional solve retrieval mode: `flash`, `focus`, or `dive`; monitoring is configured through `/observe` rather than solve mode |
| `inputs` | object | Structured inputs for skill-based or low-level calls |
| `webhook_url` | string | Optional callback for async/monitor results |
| `idempotency_key` | string | Optional key to safely retry a request; see [idempotency.md](idempotency.md) |

## Example

```json
{
  "task": "Find the cheapest RTX 6090 currently available in India and cite trustworthy sources",
  "mode": "dive"
}
```

See individual endpoint pages under [reference/](reference/search.md) for endpoint-specific fields.
