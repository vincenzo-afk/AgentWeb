# AgentWeb — Tool Assignment by Mode (v5 — semantic multi-query + full inventory)

Every tool from your pasted lists is placed below. PixelRAG and ScreamingCAT stay excluded per your earlier call.

---

## Cross-cutting rules (apply to all 4 modes)

**1. Semantic multi-query search — not literal repeats.**
Before firing search, generate N *semantically distinct* rephrasings of the task — different wording, synonyms, angle of approach — not the same string sent twice. All N variants fire **in parallel**, across all search providers assigned to that mode, then results are merged and deduped before ranking.

| Mode | Query variants |
|---|---|
| Flash | ≤ 2 (original + 1 rephrase) |
| Focus | 3–4 |
| Dive | 5–6 |
| Monitor | adaptive — starts at 2–3, adds another parallel round only if result quality/coverage is still below threshold, stops once it plateaus or hits a sane round cap (e.g. 3 rounds) so it can't loop forever |

**2. Everything fires in parallel, never sequentially** — search variants, search providers, GitHub, Reddit, and page fetches are concurrent branches.

**3. GitHub + Reddit are default branches in every mode**, not conditional on keyword detection.

**4. Self-hostable tools live only under each mode's `Self-Host` subsection** — main lists reference tools by name without inline tags.

**5. Where multiple tools do the same job**, one is named primary and the rest are fallback/alternates — ranked, not left for the Router to pick blind.

---

## ⚡ FLASH — semantic search (≤2 variants) + light fetch (2–3 pages)

- **Search (≤2 semantic variants × parallel providers):** SearXNG, Parallel Search MCP, DuckDuckGo Instant Answer
- **Fallback search (only if the above return nothing):** DuckDuckGo HTML scrape
- **Zero-click facts (parallel, same wave):** Wikidata SPARQL
- **Code branch (always parallel):** GitHub API
- **Discussion branch (always parallel):** Reddit `.json`
- **Quick-fact APIs (fired when query shape matches, parallel):** REST Countries, Open-Meteo, HackerNews API (top stories), Open Library API, Wikipedia API
- **Fetch (top 2–3, parallel, race-to-first-response):** Jina Reader primary, Trafilatura in-process alternate; underlying HTTP client is httpx

### Self-Host (Oracle)
- SearXNG

---

## 🎯 FOCUS — semantic search (3–4 variants) + multi-source fetch batch (6–8 sources, ≥3 domains)

- **Search (3–4 semantic variants × parallel providers):** SearXNG, Parallel Search MCP; DuckDuckGo HTML scrape as fallback
- **Code branch (always parallel):** GitHub API
- **Discussion branch (always parallel):** Reddit `.json` — switch to PRAW (registered app) for authenticated/deeper access; `.json` stays the default no-auth path
- **Fetch batch (6–8, parallel):**
  - Jina Reader — primary reader
  - Trafilatura — in-process alternate
  - Parser layer underneath either (one per page, as needed): BeautifulSoup default, lxml when speed matters, Selectolax for fastest parse, Parsel for XPath/CSS-style selection, Mechanize for cookie/form state
- **Structured extraction (parallel, every fetched page):** extruct, schema-dts
- **XHR interception (hidden JSON endpoints):** Playwright network interception primary, mitmproxy standalone alternate
- **Browser escalation (capped, only URLs that fail static fetch):** Playwright primary, Puppeteer alternate
- **Entity fallback (parallel):** Wikidata SPARQL, DBpedia SPARQL
- **PDF sources in the batch:** pdfplumber (tables), PyMuPDF (general text)

### Self-Host (Oracle)
- SearXNG
- Trafilatura

---

## 🌊 DIVE — semantic search (5–6 variants) + deep multi-source fetch (10–14 sources, ≥5 domains/source-types)

- **Search (5–6 semantic variants × parallel providers):** SearXNG, Parallel Search MCP, DuckDuckGo HTML scrape
- **Code branch (always parallel, deeper):** GitHub API — multiple repos, issues, releases
- **Discussion branch (always parallel):** Reddit `.json`/PRAW, Stack Exchange Network API (180+ sites incl. Stack Overflow), MathOverflow, PhilPapers, Quora Spaces (ToS-fragile — opportunistic only, not a dependency)
- **Academic branch (parallel, research-shaped tasks):** Semantic Scholar, OpenAlex, arXiv, PubMed E-utilities, CORE API, OpenReview.net
- **Books/long-form branch:** Open Library API, Project Gutenberg
- **Fetch batch (10–14, parallel):**
  - Trafilatura / Jina Reader — baseline, bulk of the batch
  - Crawl4AI — agentic extraction, LLM-optimized markdown, default for messy pages
  - ScrapeGraphAI — natural-language extraction, 1–2 sources (most expensive per call)
  - Scrapling — anti-detect scraping for protected sites
  - MediaCrawler — specialized for social platform pages
- **Browser automation (worker pool capped at 8 per `BROWSER_SPEC`):** Playwright primary, Puppeteer alternate, Selenium legacy fallback, Browser-use for autonomous multi-step interaction, Mechanize for form-heavy flows
- **XHR interception (data-heavy sites):** Playwright network interception, mitmproxy
- **Multi-page crawl (when one source needs traversal, not just one page):**
  - Scrapy — primary crawl engine
  - Crawlee — secondary, JS-aware, Playwright built in
  - Katana — fast JS-aware link discovery
  - Colly — lightweight Go crawler for large link graphs
  - Wget `--recursive` — simple recursive mirror for raw files
  - HTTrack — full offline site mirror
  - LibreCrawl — JS-rendering alternative
  - **Escalation-only, large archival crawls:** Apache Nutch, StormCrawler, Heritrix, Netpeak Spider
- **Document extraction:** pdfplumber, PyMuPDF, Camelot (PDF tables), Apache Tika (1,000+ file types)
- **Structured data mining (parallel, every fetched page):** extruct, schema-dts
- **Knowledge graph pass (parallel, on the assembled batch):** spaCy NER, Wikidata SPARQL, DBpedia SPARQL, Diffbot NLP
- **Media/transcripts (video/audio content):** youtube-dl / yt-dlp
- **Infra/domain-intel branch (security/infrastructure tasks only):** dnspython, python-whois, Shodan
- **Bulk/offline dataset tier (query a local index built from these, not a live fetch inside the 60s budget):** Common Crawl + Common Crawl WARC, Wikipedia Dumps, Hugging Face Datasets, GDELT Project, Internet Archive / Wayback Machine, Wayback CDX API, Archive.org APIs
- **Cross-session vector memory:** embed the full batch for follow-up in-session retrieval

### Self-Host (Oracle)
- SearXNG
- Qdrant (vector memory)
- Trafilatura
- Firecrawl (self-hosted Reader, backup to Jina)
- Crawlee (self-hosted, pairs with Scrapy/Katana for the crawl tier)

---

## 🛰️ MONITOR — adaptive semantic search + parallel polling + persistent streams

- **Search (adaptive, 2–3 variants per round, parallel; add another parallel round only if coverage is still weak, cap ~3 rounds):** SearXNG, Parallel Search MCP — used when Monitor needs to *discover* new sources on a topic, not just re-check known URLs

**Scheduled diff-checks (parallel batches, per-target interval):**
- changedetection.io — primary engine, 15–60 min per target
- Wayback CDX API — cheap pre-filter before hitting the live site
- deepdiff, htmldiff — structured diff once a change is flagged
- RSSHub, miniflux, FeedParser — feed sources, 5–15 min
- GitHub API — release/issue watch, 15–30 min
- Reddit `.json` — ≥10 min interval (soft-block risk faster)
- Stack Exchange Network API — new-question watch on tagged topics, 15–30 min
- GDACS, NASA DONKI RSS — hourly
- XHR discovery for stubborn targets: Playwright network interception / mitmproxy once, to find the hidden JSON endpoint, then poll that endpoint directly

**Live streams (persistent connections, separate worker pool):**
- Binance WebSocket, CoinCap WebSocket
- HackerNews Firebase real-time
- Stack Overflow real-time question stream
- Mastodon public streaming (SSE)
- OpenSky Network — poll, respect 400/day unauthenticated cap

**Webhook relay:**
- Smee.io (hosted), Hookdeck (self-host)

### Self-Host (Oracle)
- changedetection.io
- RSSHub
- miniflux
- Hookdeck
- (SearXNG / Qdrant / Trafilatura / Firecrawl / Crawlee from other modes share the same Oracle instance)

---

## Manual/local tools — not wired into the automated pipeline

Real and useful, but these are desktop/browser-extension tools a human runs, not APIs a backend service calls — listing them as live connectors would be inaccurate. Keep for manual debugging/one-off pulls, not in the request path:

- Instant Data Scraper (browser extension)
- Web Scraper.io extension
- Xenu's Link Sleuth (Windows desktop)

---

## Rate limits to track (`CONNECTOR_SPEC.md` — `rate_limit` field)

| Source | Real limit |
|---|---|
| GitHub API | 60/hr unauthenticated, 5,000/hr with token — always use a token, it's a default branch in every mode |
| Reddit `.json` / PRAW | No hard cap on `.json`, but soft-blocks on aggressive polling; PRAW needs a registered app and Reddit's 2023 API pricing changes affect authenticated commercial-scale use — `.json` stays the actually-free path |
| OpenSky | 400/day unauthenticated |
| Shodan free | 1 req/sec |
| Semantic Scholar / OpenAlex / arXiv / PubMed / CORE / OpenReview | Effectively unlimited for reasonable use, not literally infinite |
| Diffbot NLP | Free tier only, has a real cap — check current limits before relying on it in Dive |

**Multi-query note:** semantic reformulation multiplies request volume against every search provider (2–6x per call depending on mode). SearXNG being self-hosted absorbs this without external rate-limit exposure — that's the main reason it's the primary search engine in every mode rather than a hosted provider you'd have to ration.

## Structural note

Register everything as a `CONNECTOR_SPEC.md` connector with the `rate_limit` field. Where several tools do the same job, register one connector with a fallback chain (primary → alternates on failure) rather than making the Router choose blind between equivalents.
