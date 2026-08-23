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
  "session_id": "sess_abc123",
  "url": "https://example.com/product/123",
  "status": "complete",
  "actions": [
    { "index": 0, "type": "wait_for", "status": "complete" }
  ],
  "extracted": [ { "selector": ".price", "text": "₹42,999" } ],
  "title": "Product",
  "text": "Product ₹42,999",
  "html": "<html>...</html>",
  "warnings": [],
  "error": null
}
```

The optional browser extra uses Playwright with an environment-provided Chromium binary. Every request creates a fresh browser context, restricts HTTP(S) requests to the target origin and same-origin resources by default, and does not accept credentials in action payloads. Supported action types are `click`, `type`, `wait_for`, `scroll`, and `extract`. Individual actions are limited to 30 seconds and the full session to 90 seconds. Selector failures are retried once and returned as `status: "partial"` with successful prior actions preserved.

Browser sessions are sandboxed per request; see [security/sandboxing.md](../../security/sandboxing.md) and [core/browser-engine.md](../../core/browser-engine.md).
