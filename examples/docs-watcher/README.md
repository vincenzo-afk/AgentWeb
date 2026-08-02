# Example: Docs Watcher

Watches documentation or release notes for meaningful updates, using `daily` frequency (documentation changes rarely need minute-level responsiveness).

```js
const monitor = await internet.observe({
  task: "Watch the release notes page for [project] and summarize any new entries",
  webhookUrl: "https://myapp.example.com/webhooks/agentweb",
  frequency: "daily"
});
```

Pairs well with the [crawl primitive](../../docs/api/reference/crawl.md) if you need to watch an entire docs tree rather than a single page.
