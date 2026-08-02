# Citations

Every synthesized answer from `internet.solve()` is expected to be grounded: claims map back to specific sources rather than being generated unattributed.

## Response shape

```json
{
  "answer": "The cheapest listed price was found at Retailer A.",
  "sources": [
    { "id": "src_1", "url": "https://retailer-a.example.com/...", "trust_score": 0.91, "cited": true },
    { "id": "src_2", "url": "https://retailer-b.example.com/...", "trust_score": 0.74, "cited": false }
  ],
  "citations": [
    { "claim_span": [0, 55], "source_ids": ["src_1"] }
  ]
}
```

- `sources` lists all evidence considered, with a `cited` flag indicating whether it contributed to the final answer.
- `citations` maps specific spans of the answer text to the source(s) that support them.

See [concepts/explainability.md](../concepts/explainability.md) for the rationale, and [guides/citations-in-your-app.md](../guides/citations-in-your-app.md) for rendering citations in a UI.
