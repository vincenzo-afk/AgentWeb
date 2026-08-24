# Roadmap

The AgentWeb vision is broad, so delivery is phased. The early phases prove that automatic orchestration is clearly better than using separate tools; later slices extend that foundation with graph context, agent APIs, and event-driven workflows. The repository now contains an implemented local-first slice across Phases 0–4, while managed deployment and calibrated evaluation remain separate work.

## Phase 0 — MVP — implemented

The baseline grounded-research workflow is implemented through the HTTP and Python APIs:

- Grounded internet research through `solve`
- Search plus selective browsing and extraction
- Trust scoring and deterministic source ranking
- Citation-backed answer output with insufficient-evidence handling
- Monitor mode for page, price, availability, and structured-field changes through `observe`
- Lightweight tenant-scoped memory reuse for repeated targets

## Phase 1 — Depth and modes — implemented

- Retrieval modes (`flash`, `focus`, `dive`, and monitor behavior)
- Bounded same-origin crawl with durable history
- Expanded extraction for tables, entities, prices, dates, and normalized content
- Signed webhook delivery for change alerts
- Execution transparency through sources, selection logic, actions, traces, and report/replay views
- Isolated browser execution with encrypted, origin-bound reusable session state

## Phase 2 — Memory and graph — implemented initial slice

- Tenant-scoped snapshots, hashes, diffs, selective reuse, retention, and deletion
- Knowledge graph entity and relationship linking with provenance and corroboration-aware confidence
- Bounded graph-powered queries with multi-hop relationship traversal and cursor pagination
- Graph-assisted solve context grounded as source records
- Historical execution replay projections for audits and explainability
- Deterministic vector retrieval for skill fallback and cautious same-type graph entity resolution

Calibrated graph evaluation and a managed vector backend remain deployment or evaluation work rather than part of the local-first slice.

## Phase 3 — Agent-native platform — implemented initial slice

- Tenant-scoped `plan` → approval → `execute` APIs
- Execution trace and replay projections for debugging and explainability
- Built-in Internet Skills library with deterministic matching and conservative vector fallback
- Privacy-safe learning outcome persistence and aggregate evaluator feedback
- Reviewed, process-local organization-scoped connector, skill, and ranker plugins with bounded graceful fallback

Autonomous strategy adaptation is intentionally deferred until an explicit evaluation and governance design exists.

## Phase 4 — Event-driven internet — implemented initial slice

- Monitor changes, no-change checks, and fetch failures as first-class workflow events
- Durable workflow automation triggered by matching monitor events
- Supervised scheduler execution with leases, retries, rate limits, dead-letter state, and pause/resume controls
- Tenant-scoped workflow definitions and run history
- Expanded trust, observability, privacy, and organization data-deletion controls

Richer external event providers, managed operator integrations, and production load evaluation remain future work.

## Deliberate non-goals and deployment work

The repository does not implement CAPTCHA/MFA automation, a general-purpose consumer search engine, a replacement for enterprise data warehouses, a system of record for private customer data, or a legal/compliance authority. Full PostgreSQL runtime cutover, multi-node production evaluation, hosted monitoring integrations, managed plugin sandboxing, and calibrated labeled-dataset evaluation require separate deployment and governance decisions.

See [research/future-directions.md](research/future-directions.md) for longer-horizon thinking beyond this roadmap and [../spec/build-plan/IMPLEMENTATION_STATUS.md](../spec/build-plan/IMPLEMENTATION_STATUS.md) for evidence-backed module status.
