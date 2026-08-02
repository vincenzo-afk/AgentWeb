# Building Monitors

A deeper walkthrough of `internet.observe()` beyond the [quickstart](../getting-started/first-monitor.md).

## Choosing a frequency

Match check frequency to how time-sensitive the target is:
- `minutely` — slot/availability tracking where timing matters (e.g., [visa slot tracker](../../examples/visa-slot-tracker))
- `hourly` — price/stock tracking
- `daily` — documentation or policy page changes

## Defining "change that matters"

Be specific in the task description about what counts as a meaningful change (e.g., "alert only when price drops below ₹40,000," not just "alert on any change") — this reduces noisy alerts and controls cost. Under the hood this is handled by the diff engine in [core/memory.md](../core/memory.md).

## Handling alerts

```js
// webhook handler
app.post("/webhooks/agentweb", (req, res) => {
  const { event, diff } = req.body;
  if (event === "monitor.change_detected") {
    // notify user, update DB, trigger downstream workflow
  }
  res.sendStatus(200);
});
```

See [api/webhooks.md](../api/webhooks.md) for signature verification.
