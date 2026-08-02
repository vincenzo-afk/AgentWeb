# Idempotency

For POST requests that create resources (`/solve`, `/observe`, `/execute`), you can pass an `idempotency_key` to safely retry a request without triggering duplicate work or duplicate billing.

```json
{
  "task": "...",
  "idempotency_key": "client-generated-uuid"
}
```

- Reusing the same key with an identical payload returns the original result.
- Reusing the same key with a **different** payload returns a `409 conflict` error.
- Keys are honored for a limited retention window (see [operations/data-retention.md](../operations/data-retention.md)).
