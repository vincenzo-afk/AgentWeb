# Design Principles

The developer experience should be simple at the entry point and progressively more inspectable for advanced users.

1. **Start from intent, not connector configuration.** Developers describe a goal; they should not need to choose search vs. crawl vs. browser vs. monitor up front.
2. **Return grounded results with citations.** Every synthesized answer should be traceable to evidence.
3. **Show sources and execution path.** Explainability is not an add-on — it's core to trust, especially for compliance-sensitive use cases.
4. **Offer simple modes for speed versus depth.** Flash/Focus/Dive/Monitor make the tradeoff legible without requiring manual orchestration.
5. **Expose low-level control only when needed.** Advanced users can drop down to explicit primitives (search, crawl, browser, extract) when the outcome-first API doesn't fit.
6. **Make monitoring and repeated runs first-class, not bolt-ons.** Recurring tasks should benefit from memory reuse and scheduled execution, not be treated as repeated one-off calls.

## Positioning discipline

AgentWeb overlaps with several categories — search infrastructure, crawling, scraping, browser automation, monitoring, and agent infrastructure — but should not market itself as "just better search" or "just scraping plus browser." Its differentiator is orchestration + memory + graph + explainability + reusable outcomes. Product and documentation decisions should reinforce this framing rather than a feature-list framing.

## Documentation split

The full product vision is valuable but should not be the public landing page in raw form. Different documents serve different audiences:

- **Landing page** — concise, outcome-focused, category-defining messaging.
- **README** — developer-facing overview of vision, architecture, use cases, and API philosophy.
- **Technical whitepaper** — deep explanation of planner, router, memory, graph, monitoring, trust, and execution model.
- **API documentation** — endpoints, request schemas, examples, auth, billing, rate limits.
- **Investor deck** — market, category, moat, wedge, go-to-market, and why now.
- **Pitch deck** — concise narrative optimized for live presentation rather than standalone reading.

This repository's `docs/` implements the README, technical documentation, and API documentation layers; investor and pitch materials live outside the open-source docs tree.
