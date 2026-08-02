# Project Scope

## In scope (current build horizon)

- `solve` and `observe` endpoints (Phase 0/1 of [docs/roadmap.md](../../docs/roadmap.md))
- Search, crawl, browser, extract primitives
- Memory layer (snapshot/hash/diff/reuse)
- Basic trust/ranking layer
- Citation-backed synthesis
- Webhook delivery for monitors

## Explicitly out of scope for the current build horizon

- Full knowledge graph reasoning (Phase 2)
- Agent-native plan/execute/observe/diff/report APIs (Phase 3)
- Full event-driven workflow automation (Phase 4)
- See [NON_GOALS.md](NON_GOALS.md) for permanent (not just phased) exclusions.

## Scope boundary rule

A capability is in scope only if it's needed to prove the outcome-first thesis for at least one high-value workflow end-to-end (see [docs/roadmap.md](../../docs/roadmap.md) Phase 0 rationale). Anything that only makes an existing capability marginally better, without proving new ground, is deferred.
