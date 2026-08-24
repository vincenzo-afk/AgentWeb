# `POST /browser/sessions`

Low-level primitive: opens a rendered browser session for interaction, navigation, and extraction on JavaScript-heavy or flow-dependent pages where a static fetch is insufficient.

## Request

```json
{
  "url": "https://example.com/product/123",
  "credential_id": "cred_abc123",
  "actions": [
    { "type": "click", "selector": "#accept-cookies" },
    { "type": "wait_for", "selector": ".price" },
    { "type": "fill_credential", "selector": "#username", "field": "username" },
    { "type": "fill_credential", "selector": "#password", "field": "secret" },
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

The optional browser extra uses Playwright with an environment-provided Chromium binary. Every request creates a fresh browser context, restricts HTTP(S) requests to the target origin and same-origin resources by default, and does not accept raw credentials in action payloads. Administrators create credentials through `POST /admin/browser-credentials` with `label`, `username`, and `secret`; the secret is encrypted at rest with the provider-backed `AGENTWEB_BROWSER_CREDENTIAL_KEY`, and responses expose only an opaque ID and non-secret metadata. A browser request may supply that `credential_id` and use `fill_credential` actions with `field: "username"` or `field: "secret"`. Supported action types are `click`, `type`, `wait_for`, `scroll`, `extract`, and `fill_credential`. Individual actions are limited to 30 seconds and the full session to 90 seconds. Selector failures are retried once and returned as `status: "partial"` with successful prior actions preserved. Credential values are scrubbed from browser output, errors, and persisted traces.

Use `GET /admin/browser-credentials` to list safe metadata and `DELETE /admin/browser-credentials/{id}` to revoke a credential. The `admin:*` scope is required for credential lifecycle operations, while browser execution still requires `browser:execute`. Browser sessions are sandboxed per request; see [security/sandboxing.md](../../security/sandboxing.md) and [core/browser-engine.md](../../core/browser-engine.md).
