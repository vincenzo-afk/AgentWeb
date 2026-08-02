# Example: Browser Flow

Explicit, low-level browser interaction for a page requiring a click-through before the relevant content is visible.

```js
const session = await internet.browser.open({
  url: "https://example.com/product/123",
  actions: [
    { type: "click", selector: "#accept-cookies" },
    { type: "wait_for", selector: ".price" },
    { type: "extract", selector: ".price" }
  ]
});

console.log(session.results);
```

See [guides/using-browser-workflows.md](../../docs/guides/using-browser-workflows.md) and [core/browser-engine.md](../../docs/core/browser-engine.md) for how sessions are sandboxed.
