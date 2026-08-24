# Crawler Spec

## Purpose

Structured multi-page traversal with durable, organization-scoped run history. See [docs/api/reference/crawl.md](../../docs/api/reference/crawl.md).

## Interface

```text
crawl(start_url: string, max_pages: int, depth: int, url_pattern?: regex, org_id?: string) -> CrawlResult
```

## Behavior

- Traverses breadth-first by default, bounded by `max_pages` and `depth`.
- Respects `robots.txt`, a local per-host minimum interval, and the target trust policy.
- When an explicit coordination backend is configured, consumes a shared organization/host token bucket (`crawl:<host>`) before each request; the SQLite default remains local-first and does not imply a distributed service.
- Delegates individual page fetches to fetch primitives and page parsing to [PARSER_SPEC.md](PARSER_SPEC.md).
- Deduplicates URLs within a single crawl run and restricts discovered links to the start URL’s origin.
- Persists a crawl run and bounded page metadata under the authenticated organization. Successful pages also persist immutable content snapshots and bounded parser projections for later reuse.
- Records page-level status, depth, content hash, content type, title, parse warnings, and redacted errors.
- Exposes tenant-scoped run listing and detail retrieval; cross-organization lookups are nondisclosing.

## Failure modes

A crawl that reaches `max_pages` while work remains returns partial results with `truncated: true` rather than failing. A shared rate-limit rejection marks the persisted run `rate_limited` and propagates a retryable rate-limit error. Other unexpected failures mark the run `failed` and preserve already-recorded page metadata. Robots, fetch, and parsing errors are recorded as page-level outcomes where possible.
