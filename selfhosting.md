# AgentWeb self-hosting and credentialed integrations

This file records the capabilities intentionally **not wired into the default runtime**. The shipped implementation keeps the public path dependency-light, avoids embedding third-party credentials, and implements the non-credentialed public branches described in `AgentWeb-mode-tool-map.md`.

## Self-hosted services intentionally left alone

| Capability | Why it is excluded from the default path | Expected integration point |
|---|---|---|
| SearXNG | Requires an operator-managed search service and endpoint. | Configure as the primary search provider through a deployment-specific adapter. |
| Qdrant | Requires a separately hosted vector database and persistence policy. | Replace or augment the local `VectorStore`. |
| Trafilatura | Listed as an Oracle/self-hosted extraction dependency in the supplied map. | Add as a reader fallback behind the fetch/extraction interface. |
| Firecrawl | Self-hosted reader/crawl service. | Add as a bulk reader fallback for Dive. |
| Crawlee | Self-hosted crawl runtime. | Add beside the existing bounded crawler for JS-aware crawls. |
| changedetection.io | Requires a continuously running monitoring service. | Use as the primary scheduled diff engine for Monitor. |
| RSSHub | Requires a self-hosted feed adapter service. | Add as a feed discovery source for Monitor. |
| miniflux | Requires an operator-managed feed reader. | Add as a persistent feed source for Monitor. |
| Hookdeck | Self-hosted webhook relay. | Add as the relay alternative to the direct webhook sender. |

## Credentialed or restricted integrations intentionally left alone

| Capability | Credential or operational requirement |
|---|---|
| Authenticated GitHub API | The default branch uses the public GitHub API. Add `GITHUB_TOKEN` only in a deployment that needs the authenticated quota and deeper repository, issue, or release access. |
| PRAW | Requires a registered Reddit application and authenticated API access. The default path uses Reddit `.json` without an app. |
| CORE API | Requires a CORE API key. The default academic path uses OpenAlex, Semantic Scholar, arXiv, and PubMed public endpoints. |
| Shodan | Requires an API key and should only be enabled for explicitly authorized infrastructure-intelligence workflows. |
| Diffbot NLP | Requires a Diffbot token and a paid/free-tier quota decision. |
| Optional model-assisted routing | Requires an operator-managed OpenAI-compatible `/chat/completions` endpoint and API key. Set `AGENTWEB_REASONING_ENDPOINT`, `AGENTWEB_REASONING_API_KEY`, `AGENTWEB_REASONING_MODEL`, and optionally `AGENTWEB_REASONING_TIMEOUT_SECONDS`; it is disabled when these are absent. |
| Parallel Search MCP | Requires a configured remote MCP connector or hosted endpoint. The default path does not invent credentials or a connector URL. |
| Binance WebSocket | Requires an external streaming connection and a deployment that can keep a worker alive. |
| CoinCap WebSocket | Requires a persistent streaming worker. |
| Hacker News Firebase realtime | Requires a persistent stream worker rather than a request-scoped call. |
| Stack Overflow realtime stream | Requires a persistent stream worker. |
| Mastodon public streaming | Requires an instance-specific persistent SSE connection. |
| OpenSky Network | Public polling is supported only as a deployment-specific worker because the unauthenticated quota is limited. |
| mitmproxy | Requires a separately operated interception process and explicit network-traffic policy. |
| Browser automation alternates | Puppeteer, Selenium, Browser-use, and Mechanize are not added as parallel runtime dependencies; the existing isolated browser adapter remains the default. |
| ScrapeGraphAI, Scrapling, MediaCrawler | These require additional runtimes, operational controls, or site-specific policies and are not default dependencies. |
| Apache Tika, Camelot, Apache Nutch, StormCrawler, Heritrix, Netpeak Spider | These are deployment-level document or archival crawl dependencies and remain operator choices. |

## Manual or local-only tools not wired into the request path

The following tools are intentionally documented rather than exposed as live MCP connectors because they are normally run by a human in a desktop or browser-extension context:

- Instant Data Scraper
- Web Scraper.io
- Xenu's Link Sleuth
- Quora Spaces access, which is opportunistic and terms-of-service fragile

## What is implemented without this file

The default MCP server exposes Flash, Focus, Dive, and Monitor behavior; semantic query fan-out; concurrent public-source branches; GitHub repository search; Reddit `.json`; DuckDuckGo; Wikidata; Wikipedia; REST Countries; Open-Meteo; Hacker News top stories; Open Library; Stack Exchange; OpenAlex; Semantic Scholar; arXiv; PubMed; Project Gutenberg; bounded public-page extraction; same-origin crawling; browser escalation; planning; durable monitors; and monitor checks.

To add one of the excluded integrations, implement it behind the existing provider, reader, crawler, stream, or monitor interfaces and keep its credentials in deployment environment variables or an external secret manager. Do not place credentials in source code, MCP arguments, logs, traces, plans, or committed configuration.

The supplied mode map remains the authoritative inventory for these exclusions: `AgentWeb-mode-tool-map.md`.
