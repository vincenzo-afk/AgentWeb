# System Overview

AgentWeb consists of five tiers:

1. **API tier** — accepts requests (`solve`, `observe`, low-level primitives, agent APIs), handles auth, rate limiting, idempotency. See [../api/API_SPEC.md](../api/API_SPEC.md).
2. **Orchestration tier** — Planner + Router, decides strategy per request. See [../module-specs/PLANNER_SPEC.md](../module-specs/PLANNER_SPEC.md), [../module-specs/ROUTER_SPEC.md](../module-specs/ROUTER_SPEC.md).
3. **Execution tier** — Search, Crawl, Browser, Extract workers that gather raw evidence. See the corresponding `*_SPEC.md` files in [../module-specs/](../module-specs/).
4. **Intelligence tier** — Memory, Graph, Ranking/Trust, Synthesis. Converts raw evidence into a grounded, cited result.
5. **Operational tier** — Jobs/scheduling, observability, storage. See [../data/](../data/) and [../observability/](../observability/).

See [COMPONENT_DIAGRAM.md](COMPONENT_DIAGRAM.md) for how these tiers connect and [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md) for how they're deployed.
