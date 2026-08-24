# `POST /crawl`

Runs a bounded breadth-first traversal across a site, documentation collection, resource hub, or content tree. Crawls are organization-scoped and persisted in the local SQLite memory layer so the run and page metadata can be inspected after the request completes.

## Request

```json
{
  "start_url": "https://docs.example.com",
  "max_pages": 50,
  "depth": 3,
  "url_pattern": "^https://docs\\.example\\.com/.*",
  "idempotency_key": "docs-crawl-2026-08-24"
}
```

`max_pages` is bounded to 50 and `depth` to 10. The crawler remains same-origin, applies trust and `robots.txt` checks, deduplicates URLs, and records partial results when bounds are reached. A local per-host interval is always enforced. When explicit PostgreSQL distributed coordination is enabled, each organization and target host also consumes a shared token-bucket bucket named `crawl:<host>` so concurrent workers do not bypass the crawl throttle.

## Response

```json
{
  "crawl_id": "crawl_abc123",
  "pages": [
    {
      "url": "https://docs.example.com/intro",
      "status": 200,
      "extracted": true,
      "depth": 0,
      "content_hash": "…",
      "content_type": "text/html",
      "title": "Introduction",
      "parse_warnings": []
    }
  ],
  "pages_crawled": 42,
  "truncated": false
}
```

The response contains bounded metadata only. Successful pages are also stored as immutable content snapshots with bounded parser projections, allowing later memory and extraction workflows to reuse the captured content. Errors are redacted before persistence and response serialization.

## Crawl history

`GET /crawl` lists the authenticated organization’s recent crawl runs with cursor pagination. `GET /crawl/{crawl_id}` returns one run and its page metadata. A run contains its start URL, bounds, optional URL pattern, status (`running`, `completed`, `failed`, or `rate_limited`), page count, truncation flag, and timestamps. A page record contains URL, HTTP status, depth, extraction status, content hash, content type, title, parse warnings, and a redacted error when applicable.

Crawl history is tenant-scoped: another organization receives an empty list or a nondisclosing not-found response. Administrative data deletion accepts `kind: "crawls"` and removes the organization’s crawl runs and page metadata without affecting other tenants.

See [extract.md](extract.md) to turn crawled pages into structured data, and [core/router.md](../../core/router.md) for how the platform decides when crawling (versus search or a single browse) is the right strategy.
