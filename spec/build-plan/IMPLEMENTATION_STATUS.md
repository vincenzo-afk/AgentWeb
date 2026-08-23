# Implementation Status

This document maps the runnable repository to the implementation-facing specification. It is intentionally evidence-based: a module is marked implemented only when its interface, behavior, and tests exist in the source tree.

## Current build slice

| Module | Status | Evidence | Next completion work |
|---|---|---|---|
| API tier | Partial | `src/agentweb/api.py` exposes health, solve with synthesis output formats, observe/list, search, crawl, extract, memory, report, authenticated admin key/audit/usage routes, organization-scoped ownership checks, request IDs, scope auth, restricted CORS, per-identity rate limiting, cursor pagination, and idempotent mutating operations. Startup resolves platform secrets through the provider boundary. | Add full response-envelope parity and deferred plan/execute/graph endpoints only when their contracts are approved. |
| Search | Implemented | `src/agentweb/search.py` defines a pluggable provider protocol, free DuckDuckGo HTML adapter, configurable HTTP JSON provider, freshness forwarding, normalized result limits, typed provider failures, and fallback behavior. | Add licensed-provider-specific adapters and richer freshness metadata when a deployment supplies them. |
| Parser | Implemented | `src/agentweb/parser.py` parses HTML, JSON, text, and PDF fallbacks with warnings. | Add richer table and layout parsing when a dependency policy permits it. |
| Normalizer | Implemented | `src/agentweb/normalizer.py` canonicalizes prices, dates, entities, preserves raw values on failure, and emits deterministic confidence values reflecting normalization success. | Expand locale-specific date and currency coverage. |
| Crawler | Partial | `src/agentweb/crawler.py` performs bounded same-origin breadth-first traversal with URL deduplication, depth/page limits, robots handling, and truncation reporting. | Add scheduler-aware rate limiting and richer crawl persistence. |
| Extractor | Partial | `AgentWebEngine.extract` returns parsed metadata, links, warnings, trust score, overall confidence, field-level confidence, and schema-guided normalized fields with deterministic normalization confidence. | Add richer tables/entities and source-span evidence when parser contracts expand. |
| Memory | Implemented | `src/agentweb/memory.py` stores immutable organization-scoped content versions with latest lookup, hash diff, monitor state, tenant-owned scheduler jobs, leases, retries, dead-letter state, 24-hour idempotency records, and monthly usage aggregates. Production relational ownership is exposed separately through `rdbms.py`; runtime cutover remains explicit. | Add retention and task-aware reuse windows. |
| Trust Engine | Implemented | `src/agentweb/trust_engine.py` blocks unsafe target classes by default and supports explicit blocked domains. | Add robots.txt and policy-aware decisions at the crawler boundary. |
| Ranking | Implemented | `src/agentweb/ranking.py` combines trust, task relevance, and corroboration into deterministic ordering. | Consume recency and extraction-confidence signals when source metadata is available. |
| Synthesis | Partial | `src/agentweb/synthesis.py` provides deterministic text, comparison, timeline, and JSON rendering; every supported response includes source-backed citation spans, an evidence score, explicit conflicts, and `insufficient_evidence` handling. | Add richer claim segmentation and structured extraction-aware synthesis when the planner supplies field evidence. |
| Monitor | Implemented | Monitor creation, cursor-paginated listing, request-driven and scheduled checks, webhook URL persistence, usage accounting, and explicit `check_failed`/`no_change`/`change_detected` events are implemented. | Add task-specific meaningful-change policies and durable delivery-attempt records. |
| Scheduler | Implemented | `src/agentweb/scheduler.py` executes durable SQLite jobs with leases, frequency priorities, retries, and dead-letter transitions; `agentweb --worker` runs it as a separate process. | Add distributed lease coordination and queue metrics for multi-node deployments. |
| Alerting | Implemented | `src/agentweb/alerting.py` signs payloads with HMAC-SHA256 and retries bounded deliveries. | Add shared rate limiting and durable delivery-attempt records. |
| Observability | Partial | `src/agentweb/trace.py` persists secret-safe organization-scoped execution spans, including browser operations, and the API exposes tenant-filtered `/report/{execution_id}`; `KeyStore` persists immutable admin audit events; `/admin/usage` returns organization-scoped monthly usage summaries. | Add metrics, retention automation, and richer audit query controls. |
| Graph | Deferred | Explicitly post-MVP in the roadmap. | Do not implement until Phase 2 scope is approved. |
| Browser | Partial | `src/agentweb/browser.py` provides optional Playwright/Chromium sessions with fresh contexts, same-origin egress filtering, bounded actions, retries, partial results, and organization-tagged secret-safe traces. | Add a dedicated multi-process worker pool and authenticated-flow credential mechanism. |
| Planner/Router/Skills | Deferred/partial | Current engine chooses a simple URL/search path directly. | Introduce explicit plan objects only after core Phase 0 contracts are complete. |

## Build order for this iteration

This slice follows the dependency graph through the synthesis-quality boundary: **ranked evidence → deterministic coverage threshold → conflict surfacing → citation mapping → structured output formats**. Graph, agent-native APIs, and event-driven workflow automation remain out of scope because the project scope explicitly defers them.

## Done criteria for this slice

A module is considered complete only when its documented interface is implemented, failure behavior is tested with local fixtures, invariants are preserved, public behavior is documented, and the code does not persist secrets or treat an unreachable monitor as a successful no-change check. The current API slice additionally requires organization-scoped idempotency conflicts/replays, bounded cursors, and redacted usage output.

## Deliberate local-MVP constraints

The API reliability slice uses SQLite for deterministic local persistence. Idempotency records expire after 24 hours, usage is a local estimated-cost summary rather than an external invoice, and pagination is bounded to 100 records per request. These guarantees remain organization-scoped and do not imply distributed deduplication or distributed rate limiting.

The default implementation remains standard-library only. Rendered browser support is an optional free Playwright extra using an environment-provided Chromium binary. Platform secrets use a fail-closed provider boundary in staging/production; customer API keys remain PBKDF2-derived hashes, never plaintext. The optional PostgreSQL adapter provides the relational schema, required tenant indexes, bounded pooling, and additive migration import/export; the local runtime keeps SQLite snapshots/monitor state until an explicit production cutover. Snapshots, monitors, jobs, traces, keys, and audit events are organization-scoped. Scheduler execution is a separately supervised foreground worker backed by tenant-owned SQLite leases, retries, and dead-letter state. Webhooks are opt-in and are not sent unless a monitor explicitly supplies a URL and a signing secret is configured.
