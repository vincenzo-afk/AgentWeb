# Citations in Your App

How to render AgentWeb's [citation data](../api/citations.md) in a user-facing product.

## Basic rendering

```jsx
function Answer({ result }) {
  return (
    <div>
      <p>{result.answer}</p>
      <ul>
        {result.sources.filter(s => s.cited).map(s => (
          <li key={s.id}><a href={s.url}>{s.url}</a> (trust: {Math.round(s.trust_score * 100)}%)</li>
        ))}
      </ul>
    </div>
  );
}
```

## Inline citation markers

Use the `citations` array (claim-span → source mapping) to render inline footnote-style markers rather than a flat source list, if your UI supports it. This gives users a direct link between a specific claim and its evidence, consistent with the [explainability](../concepts/explainability.md) principle.

## Handling low-trust results

Consider visually flagging answers where all cited sources have low `trust_score`, or where `sources_considered` was small, so users understand result confidence.
