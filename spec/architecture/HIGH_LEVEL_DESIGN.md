# High-Level Design

## Design goals

- Outcome-first: the API surface should not require the caller to know which execution primitives are used internally.
- Explainable by default: every run must produce a full execution trace, not an opt-in one.
- Memory-first: no execution primitive should re-fetch content it has already seen and can validate as unchanged.
- Modular execution: search/crawl/browser/extract are independently scalable services behind the Router, not a monolith.

## Major subsystems

Planner, Router, Execution workers (search/crawl/browser/extract), Memory store, Graph store, Ranking engine, Synthesis engine, Job scheduler, Observability pipeline. See [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) for how these map to tiers, and [MODULES.md](MODULES.md) for a full module inventory.

## Key design decisions

See [../decisions/ARCHITECTURE_DECISIONS.md](../decisions/ARCHITECTURE_DECISIONS.md) for the rationale behind tier separation, why Planner and Router are separate components, and why Memory sits before Graph in the pipeline.
