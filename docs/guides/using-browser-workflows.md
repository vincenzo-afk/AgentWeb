# Using Browser Workflows

For pages requiring interaction — logins, multi-step forms, JS-rendered content — use the [browser primitive](../api/reference/browser.md) directly, or let the [Router](../core/router.md) escalate to it automatically within `internet.solve()`.

## Automatic escalation through solve

For an absolute URL, explicit rendering or interaction wording routes the URL through the isolated browser engine while ordinary direct-URL summaries continue to use static extraction:

```json
{
  "task": "Render and summarize https://example.com/product/123",
  "inputs": {
    "actions": [
      { "type": "wait_for", "selector": ".price" },
      { "type": "extract", "selector": ".price" }
    ]
  }
}
```

The solve response records the browser stage in its bounded `actions` summary. If `inputs` includes `credential_id` or `session_state_id`, only the opaque reference is forwarded; the engine resolves it with the same tenant and origin checks as the direct browser endpoint. Invalid references fail closed.

## Direct control example

```js
const session = await internet.browser.open({
  url: "https://example.com/product/123",
  actions: [
    { type: "click", selector: "#accept-cookies" },
    { type: "wait_for", selector: ".price" },
    { type: "extract", selector: ".price" }
  ]
});
```

## Reusing authorized authentication state

An authorized operator can first create encrypted Playwright-compatible storage state through `POST /admin/browser-session-states`. The endpoint accepts a label, one absolute HTTP(S) origin, and a state object containing cookies and/or origin local storage, but returns only non-secret metadata. A later browser request may supply the returned opaque ID:

```json
{
  "url": "https://example.com/account",
  "session_state_id": "bstate_abc123",
  "actions": [
    { "type": "wait_for", "selector": ".account-menu" },
    { "type": "extract", "selector": ".account-menu" }
  ]
}
```

State is decrypted only for the authenticated organization and the same normalized origin. Revoked, malformed, oversized, cross-tenant, and cross-origin state is rejected; session tokens are never returned in browser results, traces, or metadata listings. Use `DELETE /admin/browser-session-states/{id}` to revoke one state, or `DELETE /admin/data` with `kind: "session_states"` to remove all state for the organization.

## Best practices

- Prefer `wait_for` over fixed delays; pages render at variable speed.
- Keep action sequences minimal — each additional step adds latency and a potential failure point.
- For recurring targets, pair with [Building Monitors](building-monitors.md) so the interaction sequence is reused rather than re-authored per check.

See [core/browser-engine.md](../core/browser-engine.md) for the underlying sandboxing model.
