# Implementation Status

This document maps the runnable repository to the implementation-facing specification. It is intentionally evidence-based: a module is marked implemented only when its interface, behavior, and tests exist in the source tree.

## Current build slice

| Module | Status | Evidence | Next completion work |
|---|---|---|---|
| API tier | Partial | `src/agentweb/api.py` exposes health, solve, observe, search, crawl, extract, memory, and report routes with request IDs, scope auth, and a process-local rate limiter. | Add durable API-key storage, idempotency records, and complete endpoint parity. |
| Search | Partial | `src/agentweb/search.py` provides a public HTML adapter with normalized URL/title/snippet output. | Add provider interface, freshness handling, retry policy, and typed failures. |
| Parser | Implemented | `src/agentweb/parser.py` parses HTML, JSON, text, and PDF fallbacks with warnings. | Add richer table and layout parsing when a dependency policy permits it. |
| Normalizer | Implemented | `src/agentweb/normalizer.py` canonicalizes prices, dates, entities, and preserves raw values on failure. | Expand locale-specific date and currency coverage. |
| Crawler | Partial | `src/agentweb/crawler.py` performs bounded same-origin breadth-first traversal with URL deduplication, depth/page limits, robots handling, and truncation reporting. | Add scheduler-aware rate limiting and richer crawl persistence. |
| Extractor | Partial | `AgentWebEngine.extract` returns parsed metadata, links, warnings, trust score, and schema-guided normalized fields. | Add per-field confidence and richer tables/entities. |
| Memory | Implemented | `src/agentweb/memory.py` stores immutable content versions with latest lookup, hash diff, and monitor state. | Add retention and task-aware reuse windows. |
| Trust Engine | Implemented | `src/agentweb/trust_engine.py` blocks unsafe target classes by default and supports explicit blocked domains. | Add robots.txt and policy-aware decisions at the crawler boundary. |
| Ranking | Implemented | `src/agentweb/ranking.py` combines trust, task relevance, and corroboration into deterministic ordering. | Add recency and extraction-confidence signals when source metadata is available. |
| Synthesis | Partial | `solve` returns source-backed text, citation spans, and explicit `insufficient_evidence`. | Add conflict-aware output metadata and richer structured formats. |
| Monitor | Implemented | Monitor creation, request-driven and scheduled checks, webhook URL persistence, and explicit `check_failed`/`no_change`/`change_detected` events are implemented. | Add task-specific meaningful-change policies and durable delivery-attempt records. |
| Scheduler | Implemented | `src/agentweb/scheduler.py` executes durable SQLite jobs with leases, frequency priorities, retries, and dead-letter transitions; `agentweb --worker` runs it as a separate process. | Add distributed lease coordination and queue metrics for multi-node deployments. |
| Alerting | Implemented | `src/agentweb/alerting.py` signs payloads with HMAC-SHA256 and retries bounded deliveries. | Add shared rate limiting and durable delivery-attempt records. |
| Observability | Partial | `src/agentweb/trace.py` persists secret-safe execution spans, including browser operations, and the API exposes `/report/{execution_id}`. | Add metrics and audit-event storage. |
| Graph | Deferred | Explicitly post-MVP in the roadmap. | Do not implement until Phase 2 scope is approved. |
| Browser | Partial | `src/agentweb/browser.py` provides optional Playwright/Chromium sessions with fresh contexts, same-origin egress filtering, bounded actions, retries, and partial results. | Add a dedicated multi-process worker pool and authenticated-flow credential mechanism. |
| Planner/Router/Skills | Deferred/partial | Current engine chooses a simple URL/search path directly. | Introduce explicit plan objects only after core Phase 0 contracts are complete. |

## Build order for this iteration

This slice follows the dependency graph through the Phase 1 browser and scheduler foundations: **Browser → durable monitor jobs → leased worker execution → API/CLI integration**. Graph, agent-native APIs, and event-driven workflow automation remain out of scope because the project scope explicitly defers them.

## Done criteria for this slice

A module is considered complete only when its documented interface is implemented, failure behavior is tested with local fixtures, invariants are preserved, public behavior is documented, and the code does not persist secrets or treat an unreachable monitor as a successful no-change check.

## Deliberate local-MVP constraints

The default implementation remains standard-library only. Rendered browser support is an optional free Playwright extra using an environment-provided Chromium binary. Public search and HTTP fetches are adapter boundaries and are not used by deterministic tests. Scheduler execution is a separately supervised foreground worker backed by SQLite leases, retries, and dead-letter state. Webhooks are opt-in and are not sent unless a monitor explicitly supplies a URL and a signing secret is configured.
