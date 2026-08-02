# `POST /browser/sessions`

Low-level primitive: opens a rendered browser session for interaction, navigation, and extraction on JavaScript-heavy or flow-dependent pages where a static fetch is insufficient.

## Request

```json
{
  "url": "https://example.com/product/123",
  "actions": [
    { "type": "click", "selector": "#accept-cookies" },
    { "type": "wait_for", "selector": ".price" },
    { "type": "extract", "selector": ".price" }
  ]
}
```

## Response

```json
{
  "session_id": "bsess_abc123",
  "final_url": "https://example.com/product/123",
  "results": [ { "selector": ".price", "text": "₹42,999" } ]
}
```

Browser sessions are sandboxed per request; see [security/sandboxing.md](../../security/sandboxing.md) and [core/browser-engine.md](../../core/browser-engine.md).
