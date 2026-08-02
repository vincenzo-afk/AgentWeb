# Quickstart

A minimal end-to-end example: ask AgentWeb to research something and return a cited answer.

```js
import { AgentWeb } from "@agentweb/sdk";

const internet = new AgentWeb({ apiKey: process.env.AGENTWEB_API_KEY });

const result = await internet.solve({
  task: "Find the cheapest RTX 6090 currently available in India and cite trustworthy sources"
});

console.log(result.answer);
console.log(result.sources);
```

The response includes:

- `answer` — the synthesized, grounded response
- `sources` — the evidence used, with citation-level attribution
- `mode` — the retrieval mode actually used (unless overridden, the planner chooses this)
- `execution_id` — a reference for inspecting the full execution graph later

Try setting up recurring monitoring next: [Your First Monitor](first-monitor.md), or dig into a single query in more depth: [Your First Query](first-query.md).
