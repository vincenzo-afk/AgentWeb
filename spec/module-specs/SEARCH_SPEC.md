# Search Spec

## Purpose
Fast retrieval of links/snippets/candidate sources. See [docs/api/reference/search.md](../../docs/api/reference/search.md) for the public API contract.

## Interface
```
search(query: string, limit?: int, freshness?: string) -> SearchResult[]
```

## Behavior
- Queries an underlying search index/provider abstraction (pluggable; see [CONNECTOR_SPEC.md](CONNECTOR_SPEC.md)).
- Returns URL, title, snippet, and published date where available.
- Does not render pages — see [BROWSER_SPEC.md](BROWSER_SPEC.md) for that.

## Performance target
p95 latency target: see [../testing/PERFORMANCE_TARGETS.md](../testing/PERFORMANCE_TARGETS.md) (`flash` mode budget).
