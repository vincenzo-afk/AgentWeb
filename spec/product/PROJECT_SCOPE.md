# Project Scope

## In scope (current build horizon)

- `solve`, `observe`, and authenticated agent-native `plan` → approval → `execute` endpoints
- Search, crawl, browser, extract, and bounded connector/plugin primitives
- Memory layer (snapshot/hash/diff/reuse) with tenant-scoped retention and deletion
- Trust, deterministic ranking, and citation-backed synthesis
- Tenant-scoped knowledge graph storage, provenance, bounded multihop queries, and graph-assisted solve context
- Deterministic vector retrieval for skills and cautious graph entity resolution
- Privacy-safe learning outcome persistence and aggregate evaluator feedback
- Monitor change/no-change/check-failed events and durable event-driven workflow runs
- Signed webhook delivery and supervised local scheduler execution

## Explicitly deferred or deployment-scoped work

- CAPTCHA/MFA automation and provider-specific browser session bootstrap
- Rich external event-provider integrations and managed connector persistence
- Calibrated graph, ranking, synthesis, monitor, and extraction evaluation against approved labeled datasets
- Autonomous strategy adaptation without an explicit evaluation and governance design
- Full relational runtime cutover, multi-node load evaluation, and hosted/operator integrations

See [NON_GOALS.md](NON_GOALS.md) for permanent exclusions and the [implementation status ledger](../build-plan/IMPLEMENTATION_STATUS.md) for evidence-backed module status.

## Scope boundary rule

A capability is in scope only if it is needed to prove the outcome-first thesis for at least one high-value workflow end-to-end (see [docs/roadmap.md](../../docs/roadmap.md) Phase 0 rationale). Features that extend the implemented local workflow without a concrete contract remain deferred until their interfaces, safety policy, and evaluation plan are approved.
