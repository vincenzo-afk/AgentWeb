# Project Memory

Running log of context a future agent/session needs, so decisions aren't re-derived or re-litigated from scratch. Append entries chronologically; don't rewrite history here — use [DECISION_HISTORY.md](DECISION_HISTORY.md) for formal decision records and [LESSONS_LEARNED.md](LESSONS_LEARNED.md) for retrospective insight.

## Format

```
## [YYYY-MM-DD] <short title>
Context: <what prompted this entry>
Note: <what a future agent needs to know>
Related: <links to spec files, ADRs, or issues>
```

## Entries

## [Initial] Spec tree created
Context: Full build-spec tree generated from product vision + competitive frame source documents, organized under `spec/` alongside the existing developer-facing `docs/` tree.
Note: `docs/` is usage-facing prose (audience: integrators); `spec/` is build-facing (audience: implementers/agents). Keep them consistent but don't merge them — see [../standards/DOCUMENTATION_STANDARDS.md](../standards/DOCUMENTATION_STANDARDS.md).
Related: [../standards/NAMING_CONVENTIONS.md](../standards/NAMING_CONVENTIONS.md)

<!-- Add new entries above this line as the build progresses -->
