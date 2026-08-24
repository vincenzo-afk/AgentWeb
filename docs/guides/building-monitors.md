# Building Monitors

A deeper walkthrough of `internet.observe()` beyond the [quickstart](../getting-started/first-monitor.md).

## Choosing a frequency

Match check frequency to how time-sensitive the target is:

| Frequency | Suitable use |
|---|---|
| `minutely` | Slot or availability tracking where timing matters, such as the [visa slot tracker](../../examples/visa-slot-tracker). |
| `hourly` | Price or stock tracking. |
| `daily` | Documentation, release notes, or policy page changes. |

## Defining “change that matters”

Be specific in the task description about what counts as a meaningful change, such as “alert only when price drops below ₹40,000,” rather than just “alert on any change.” This reduces noisy alerts and controls cost. Under the hood, the comparison is handled by the diff engine in [core/memory.md](../core/memory.md).

For a parsed table or JSON response, use a structured-field policy when unrelated page changes should not trigger an alert:

```json
{
  "task": "Watch the first product price in the catalog table",
  "frequency": "hourly",
  "change_policy": {
    "kind": "structured_field",
    "field_path": "tables.0.1.1",
    "expected_type": "price",
    "absolute_delta": 100,
    "relative_delta_percent": 5
  }
}
```

For JSON, the decoded document is under `data`, so a price property is addressed as `data.price`. Paths are intentionally bounded dotted paths over the parser projection, not arbitrary JSONPath expressions. Dictionary keys and numeric list indexes are supported; missing keys and out-of-range indexes are treated as missing. Missing on both checks is stable, while a missing-to-present or present-to-missing transition is meaningful.

The `expected_type` can be `string`, `entity`, `price`, or `date`. Prices and dates use deterministic locale-aware normalization, and strings can set `ignore_whitespace` to collapse spacing differences. Absolute and relative thresholds are valid only for `price`. If a value cannot be normalized, AgentWeb retains the raw value and compares it deterministically rather than guessing.

Structured projections are stored alongside immutable snapshots for monitor comparison. They are not exposed as an unrestricted snapshot export. A failed fetch, trust decision, or parsing boundary produces `check_failed`; it must never be interpreted as `no_change`.

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
