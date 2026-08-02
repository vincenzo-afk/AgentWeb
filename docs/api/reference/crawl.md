# `POST /crawl`

Low-level primitive: structured traversal across a site, documentation collection, resource hub, or content tree. Useful for breadth over a domain or recurring indexing, as opposed to a single-page fetch.

## Request

```json
{
  "start_url": "https://docs.example.com",
  "max_pages": 100,
  "depth": 3,
  "url_pattern": "^https://docs\\.example\\.com/.*"
}
```

## Response

```json
{
  "pages": [
    { "url": "https://docs.example.com/intro", "status": 200, "extracted": true }
  ],
  "pages_crawled": 42
}
```

See [extract.md](extract.md) to turn crawled pages into structured data, and [core/router.md](../../core/router.md) for how the platform decides when crawling (vs. search or a single browse) is the right strategy.
