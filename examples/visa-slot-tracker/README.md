# Example: Visa Slot Tracker

High-frequency monitoring of an availability page, demonstrating the `minutely` frequency tier.

```js
const monitor = await internet.observe({
  task: "Track visa appointment slot availability for [location] and alert immediately when a new slot appears",
  webhookUrl: "https://myapp.example.com/webhooks/agentweb",
  frequency: "minutely"
});
```

Because this is a time-sensitive, high-frequency use case, be specific about what counts as a new slot (vs. a page re-render with no real change) to avoid noisy alerts — see [guides/building-monitors.md](../../docs/guides/building-monitors.md#defining-change-that-matters).
