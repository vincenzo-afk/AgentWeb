# Lessons Learned

Retrospective insights, distinct from [PROJECT_MEMORY.md](PROJECT_MEMORY.md) (ongoing context) and [DECISION_HISTORY.md](DECISION_HISTORY.md) (specific decisions). This file captures patterns worth remembering across the whole project.

## Format

```
## [Area] <lesson title>
What happened: <brief>
Lesson: <the generalizable takeaway>
Applies to: <which future work this should inform>
```

## Seeded lessons (from spec design, before implementation begins)

## [Documentation] Redundant filenames across doc trees create drift risk
What happened: This spec tree (`spec/`) and the earlier prose doc tree (`docs/`) cover overlapping ground under different naming conventions.
Lesson: Where a `spec/` file's content is a redirect to `docs/`, keep it a genuine redirect (not a partial copy) — partial copies drift out of sync silently. See [../standards/DOCUMENTATION_STANDARDS.md](../standards/DOCUMENTATION_STANDARDS.md).
Applies to: Any future addition to either doc tree that duplicates existing content.

## [Scope] Broad vision docs need explicit non-goals to stay buildable
What happened: The product vision spans search, crawl, browser, memory, graph, monitoring, agents, and event-driven workflows — broad enough to never finish if treated as one flat backlog.
Lesson: [../product/NON_GOALS.md](../product/NON_GOALS.md) and phase-gated [../build-plan/PHASES.md](../build-plan/PHASES.md) are what make the vision buildable; any new feature request should be checked against both before being added to scope.
Applies to: Roadmap/scope changes at any point in the project.

<!-- Add new entries above this line as real implementation lessons emerge -->
