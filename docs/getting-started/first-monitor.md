# Your First Monitor

`internet.observe()` sets up a recurring task that watches a target and alerts you on change.

```js
const monitor = await internet.observe({
  task: "Track visa slot availability and alert when a new slot appears",
  webhook_url: "https://myapp.example.com/webhooks/agentweb"
});
```

## What happens internally

AgentWeb schedules periodic checks, uses the **memory layer** to snapshot and hash the target's state, and computes a **diff** against the previous snapshot. When a meaningful change is detected, it triggers a webhook (or, in Phase 4, a downstream workflow — see [concepts/event-driven-internet.md](../concepts/event-driven-internet.md)).

## Common monitor targets

- Product/price pages (see [examples/product-comparison](../../examples/product-comparison))
- Documentation and release notes (see [examples/docs-watcher](../../examples/docs-watcher))
- Slot/availability pages (see [examples/visa-slot-tracker](../../examples/visa-slot-tracker))
- Competitor pages generally (see [examples/monitoring-agent](../../examples/monitoring-agent))

See [api/reference/monitor.md](../api/reference/monitor.md) for the full schema, and [guides/building-monitors.md](../guides/building-monitors.md) for a deeper walkthrough.
