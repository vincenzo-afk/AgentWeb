# Idempotency

Mutating requests (`/solve`, `/observe`, `/admin/keys`, and destructive DELETE routes) accept an `Idempotency-Key` header. POST bodies may also use the `idempotency_key` field for compatibility. Keys are scoped to the authenticated organization and prevent duplicate work or duplicate billing during retries.

```http
Idempotency-Key: client-generated-uuid
```

```json
{
  "task": "...",
  "idempotency_key": "client-generated-uuid"
}
```

Reusing the same key with an identical semantic payload returns the original status and response body. The idempotency field itself is excluded from the payload comparison. Reusing a key with a different payload returns a `409 conflict` error; a concurrent retry while the original request is running also returns `409` rather than triggering duplicate work. Keys are honored for a limited retention window (see [operations/data-retention.md](../operations/data-retention.md)).
