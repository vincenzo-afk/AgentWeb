# Task Breakdown

## Phase 0 (MVP) — sample task-level breakdown

**Search**
- [x] Provider abstraction interface
- [x] Result normalization (title/snippet/url/date)
- [x] Freshness filtering

**Extractor / Parser / Normalizer**
- [x] HTML parsing + readability extraction
- [x] Schema-guided extraction mode
- [x] Field-type normalization (price, date, entity name)
- [x] Tables, entities, and source-local evidence spans

**Memory**
- [x] Content-addressed snapshot storage
- [x] Hash comparison + diff computation
- [x] Reuse-policy freshness check
- [x] Retention cleanup and tenant-scoped data deletion

**Ranking / Synthesis**
- [x] Basic trust scoring (reputation + recency signals only for MVP)
- [x] Citation mapping (claim span → source ids)
- [x] Insufficient-evidence handling path
- [x] Recency, content-type, and extraction-confidence ranking signals

**Monitor / Alerting**
- [x] Scheduler + frequency tiers
- [x] Webhook signing + delivery + retry
- [x] Task-aware monitor change policies

**API tier**
- [x] `/solve`, `/observe` endpoints
- [x] Auth, rate limiting, idempotency
- [x] Organization-scoped metrics endpoint and response rate-limit headers
- [x] Organization-scoped data deletion endpoint

See [../testing/ACCEPTANCE_CRITERIA.md](../testing/ACCEPTANCE_CRITERIA.md) for what "done" means per task. Graph storage/query, planner/execute, workflow automation, vector retrieval, privacy-safe learning persistence, and bounded organization-scoped plugins are implemented slices. PostgreSQL runtime cutover, browser credential flows, calibrated evaluation, and production staging gates remain open readiness work.
