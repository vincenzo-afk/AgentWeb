# Your First Query

`internet.solve()` is the primary entry point for one-shot, grounded research tasks.

```js
const result = await internet.solve({
  task: "Compare AI startups competing with Company X that raised funding this month and released a new GitHub project",
  mode: "dive" // optional — omit to let the planner choose
});
```

## What happens internally

1. The **planner** interprets the task and decides what kind of work is needed (search-only, search + browse, multi-source comparison, etc.). See [core/planner.md](../core/planner.md).
2. The **router** selects concrete tools and sources. See [core/router.md](../core/router.md).
3. The **execution layer** gathers evidence (search results, browsed pages, extracted structured data).
4. The **memory layer** reuses anything already known about relevant targets.
5. The **ranking/trust layer** scores sources.
6. The **synthesis layer** produces the final cited answer.

## Inspecting the result

```js
console.log(result.answer);      // synthesized answer
console.log(result.sources);     // cited evidence
console.log(result.mode);        // retrieval mode used
console.log(result.execution_id) // for later inspection, see debugging-basics.md
```

See [api/reference/solve.md](../api/reference/solve.md) for the full request/response schema, and [concepts/retrieval-modes.md](../concepts/retrieval-modes.md) to control speed vs. depth.
