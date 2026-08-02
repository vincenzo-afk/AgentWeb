# Example: Monitoring Agent

Generic competitor/page monitoring using `internet.observe()`, with a webhook handler that routes alerts.

```js
const monitor = await internet.observe({
  task: "Watch Company X's pricing page and blog for any changes",
  webhookUrl: "https://myapp.example.com/webhooks/agentweb",
  frequency: "daily"
});
```

```js
app.post("/webhooks/agentweb", (req, res) => {
  const { event, diff } = req.body;
  if (event === "monitor.change_detected") {
    notifyTeam(diff.summary);
  }
  res.sendStatus(200);
});
```

See [guides/building-monitors.md](../../docs/guides/building-monitors.md) for frequency and alert-tuning guidance.
