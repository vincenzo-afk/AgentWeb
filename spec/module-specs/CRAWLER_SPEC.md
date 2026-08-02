# Crawler Spec

## Purpose
Structured multi-page traversal. See [docs/api/reference/crawl.md](../../docs/api/reference/crawl.md).

## Interface
```
crawl(start_url: string, max_pages: int, depth: int, url_pattern?: regex) -> CrawlResult
```

## Behavior
- Breadth-first traversal by default, bounded by `max_pages` and `depth`.
- Respects `robots.txt` and per-target rate limits (see [../security/SECURITY_MODEL.md](../security/SECURITY_MODEL.md)).
- Delegates individual page fetches to Search/Browser primitives and page parsing to [PARSER_SPEC.md](PARSER_SPEC.md).
- Deduplicates URLs within a single crawl run.

## Failure modes
Crawl exceeds `max_pages` before completing target pattern coverage → return partial results with a `truncated: true` flag rather than failing.
