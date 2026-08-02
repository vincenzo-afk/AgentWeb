# Roadmap

The AgentWeb vision is broad, so delivery is phased. The goal of the early phases is to prove that automatic orchestration is clearly better than using separate tools, before expanding into graph reasoning, agent APIs, and full event-driven workflows.

## Phase 0 — MVP

A sensible early product direction proves one high-value workflow where automatic orchestration is clearly better than separate tools:

- One API endpoint for grounded internet research (`internet.solve`)
- Search plus selective browsing and extraction
- Basic trust scoring and source ranking
- Citation-backed answer output
- A monitor mode for page or price changes (`internet.observe`)
- Lightweight memory reuse for repeated targets

This validates the core promise while leaving graph expansion, advanced agent APIs, and full event-driven workflows for later phases.

## Phase 1 — Depth and modes

- Retrieval modes (Flash / Focus / Dive / Monitor) exposed as first-class options
- Crawl layer for structured, multi-page traversal
- Expanded extraction (tables, entities, prices, dates, normalized content)
- Webhook delivery for monitor alerts
- Execution transparency in API responses (sources, selection logic, actions taken)

## Phase 2 — Memory and graph

- Full memory layer: snapshot, hash, diff, selective refresh across all task types
- Knowledge graph layer: entity and relationship linking across sources and time
- Graph-powered queries (multi-hop, relationship-aware)
- Historical replay for audits and explainability

## Phase 3 — Agent-native platform

- Agent APIs: `plan`, `execute`, `observe`, `diff`, `report`
- Execution graph inspector for debugging, replay, and intervention
- Internet Skills library (reusable strategy templates for recurring task classes)
- Learning loop: successful orchestration strategies stored and reused across tasks

## Phase 4 — Event-driven internet

- Treat internet changes as first-class triggers (price drops, releases, policy updates, slot availability)
- Workflow automation triggered directly by detected events
- Deeper enterprise trust, observability, and compliance tooling

## Non-goals (for now)

- Building a general-purpose consumer search engine
- Replacing enterprise data warehouses or internal knowledge bases
- Acting as a system of record for anything beyond internet-derived evidence

See [research/future-directions.md](research/future-directions.md) for longer-horizon thinking beyond this roadmap.
