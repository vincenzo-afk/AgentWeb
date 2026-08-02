# Task Breakdown

## Phase 0 (MVP) — sample task-level breakdown

**Search**
- [ ] Provider abstraction interface
- [ ] Result normalization (title/snippet/url/date)
- [ ] Freshness filtering

**Extractor / Parser / Normalizer**
- [ ] HTML parsing + readability extraction
- [ ] Schema-guided extraction mode
- [ ] Field-type normalization (price, date, entity name)

**Memory**
- [ ] Content-addressed snapshot storage
- [ ] Hash comparison + diff computation
- [ ] Reuse-policy freshness check

**Ranking / Synthesis**
- [ ] Basic trust scoring (reputation + recency signals only for MVP)
- [ ] Citation mapping (claim span → source ids)
- [ ] Insufficient-evidence handling path

**Monitor / Alerting**
- [ ] Scheduler + frequency tiers
- [ ] Webhook signing + delivery + retry

**API tier**
- [ ] `/solve`, `/observe` endpoints
- [ ] Auth, rate limiting, idempotency

See [../testing/ACCEPTANCE_CRITERIA.md](../testing/ACCEPTANCE_CRITERIA.md) for what "done" means per task.
