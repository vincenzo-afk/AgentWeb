# `GET /memory/{target}`

Direct access to stored snapshots for a target (a URL, entity, or monitor).

## Request

```
GET /memory/https%3A%2F%2Fexample.com%2Fproduct%2F123
```

## Response

```json
{
  "target": "https://example.com/product/123",
  "snapshots": [
    { "hash": "a1b2c3", "captured_at": "2026-07-29T08:00:00Z" },
    { "hash": "d4e5f6", "captured_at": "2026-07-31T08:00:00Z" }
  ]
}
```

## `GET /memory/{target}/diff`

```
GET /memory/https%3A%2F%2Fexample.com%2Fproduct%2F123/diff?from=a1b2c3&to=d4e5f6
```

```json
{
  "changed_fields": ["price"],
  "summary": "Price dropped from ₹44,999 to ₹42,999"
}
```

See [concepts/memory-model.md](../../concepts/memory-model.md) and [core/memory.md](../../core/memory.md).
