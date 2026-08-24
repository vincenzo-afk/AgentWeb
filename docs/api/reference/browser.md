# `POST /browser/sessions`

Low-level primitive: opens a rendered browser session for interaction, navigation, and extraction on JavaScript-heavy or flow-dependent pages where a static fetch is insufficient.

## Request

```json
{
  "url": "https://example.com/product/123",
  "credential_id": "cred_abc123",
  "session_state_id": "bstate_abc123",
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

The optional browser extra uses Playwright with an environment-provided Chromium binary. Every request creates a fresh browser context and, by default, runs through a bounded spawned browser-worker process pool. Worker processes are created lazily, capped at eight, recycled after a bounded number of tasks, and terminated on session timeout or explicit engine shutdown. `AGENTWEB_BROWSER_PROCESS_WORKERS=0` disables process dispatch and retains the direct in-process execution path; the default is one worker process.

Each session remains isolated per request, restricts HTTP(S) requests to the target origin and same-origin resources by default, and does not accept raw credentials in action payloads. Administrators create credentials through `POST /admin/browser-credentials` with `label`, `username`, and `secret`; the secret is encrypted at rest with the provider-backed `AGENTWEB_BROWSER_CREDENTIAL_KEY`, and responses expose only an opaque ID and non-secret metadata. A browser request may supply that `credential_id` and use `fill_credential` actions with `field: "username"` or `field: "secret"`.

Authorized operators can create reusable encrypted Playwright-compatible storage state through `POST /admin/browser-session-states` with `label`, an absolute HTTP(S) `origin`, and a JSON `state` containing cookies and/or origin storage. The response and `GET /admin/browser-session-states` expose only `id`, label, normalized origin, timestamps, and revocation metadata; cookie values, local-storage values, and session tokens are never returned. Supply the resulting `session_state_id` to `/browser/sessions` only for the same origin. State is resolved only for the authenticated organization, and cross-origin or revoked references are rejected. Use `DELETE /admin/browser-session-states/{id}` to revoke state. `DELETE /admin/data` accepts `kind: "session_states"` for organization-wide cleanup.

Supported action types are `click`, `type`, `wait_for`, `scroll`, `extract`, and `fill_credential`. Individual actions are limited to 30 seconds and the full session to 90 seconds. Selector failures are retried once and returned as `status: "partial"` with successful prior actions preserved. Worker-process timeouts remain retryable browser errors, and typed availability/action errors are preserved across the process boundary. Credential values and injected session-state values are scrubbed from browser output, errors, and persisted traces. Session state is encrypted at rest and is not returned by browser responses.

Use `GET /admin/browser-credentials` to list safe metadata and `DELETE /admin/browser-credentials/{id}` to revoke a credential. Use `GET /admin/browser-session-states` to list safe session-state metadata and `DELETE /admin/browser-session-states/{id}` to revoke state. The `admin:*` scope is required for credential and session-state lifecycle operations, while browser execution still requires `browser:execute`. Browser sessions are sandboxed per request; see [security/sandboxing.md](../../security/sandboxing.md) and [core/browser-engine.md](../../core/browser-engine.md).
