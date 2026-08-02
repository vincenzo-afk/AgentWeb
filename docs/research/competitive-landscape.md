# Competitive Landscape

AgentWeb overlaps with multiple categories rather than sitting neatly in one: search infrastructure, crawling tools, scraping systems, browser automation platforms, monitoring products, and agent infrastructure.

Browser-focused platforms already position browser sessions, search, and fetch as a combined stack for agent workflows, which validates part of the architectural direction — but AgentWeb's ambition is to unify those layers with memory, graph, monitoring, and synthesis into one programmable intelligence system, rather than stopping at a combined-tools offering.

## Positioning discipline

Because of this overlap, the product should not market itself as "just better search" or "just scraping plus browser." Its differentiator is orchestration + memory + graph + explainability + reusable outcomes — see [concepts/internet-intelligence.md](../concepts/internet-intelligence.md) and [design-principles.md](../design-principles.md).

## Category segments touched

| Category | How AgentWeb relates |
|---|---|
| Search APIs | Subsumed as one execution primitive, not the product itself |
| Crawling/scraping tools | Subsumed as execution primitives |
| Browser automation platforms | Treated as a first-class pillar, not a bolt-on |
| Monitoring/change-detection products | A core mode (`observe`), not a separate product |
| Agent infrastructure | A target consumer segment, addressable via [Agent APIs](../concepts/agents.md) |
