# Outcomes over Tools

Most internet retrieval products expose tools — `search()`, `crawl()`, `browser.extract()` — and leave orchestration to the developer. AgentWeb inverts this: developers describe an **outcome** (research a company, compare products, monitor a competitor) and the platform decides which tools to use, in what order, and how to combine results.

```js
// Tool-first (what AgentWeb avoids requiring)
const links = await search(query);
const page = await browser.open(links[0]);
const data = await extract(page);

// Outcome-first (AgentWeb's model)
const result = await internet.solve({ task: "..." });
```

This doesn't remove low-level control — advanced users can still call search, crawl, browser, and extract directly (see [api/reference](../api/index.md)) — but the default path optimizes for describing *what* you want, not *how* to get it.

The practical benefit compounds over time: because the platform owns orchestration, it can learn which strategies work best for which task classes and reuse them — see [Internet Skills](internet-skills.md) and the learning-moat discussion in [research/economic-model.md](../research/economic-model.md).
