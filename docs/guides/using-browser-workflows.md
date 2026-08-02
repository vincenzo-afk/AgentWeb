# Using Browser Workflows

For pages requiring interaction — logins, multi-step forms, JS-rendered content — use the [browser primitive](../api/reference/browser.md) directly, or let the [Router](../core/router.md) escalate to it automatically within `internet.solve()`.

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

## Best practices

- Prefer `wait_for` over fixed delays; pages render at variable speed.
- Keep action sequences minimal — each additional step adds latency and a potential failure point.
- For recurring targets, pair with [Building Monitors](building-monitors.md) so the interaction sequence is reused rather than re-authored per check.

See [core/browser-engine.md](../core/browser-engine.md) for the underlying sandboxing model.
