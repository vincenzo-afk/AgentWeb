# Architecture Decisions (ADR Index)

| ADR | Decision | Status |
|---|---|---|
| ADR-001 | Separate Planner and Router into distinct components | Accepted |
| ADR-002 | Memory layer sits before Graph layer in the pipeline | Accepted |
| ADR-003 | Outcome-first API (`solve`/`observe`) as the primary surface, low-level primitives secondary | Accepted |
| ADR-004 | Content-addressed (hash-based) snapshot storage over versioned-row storage | Accepted |
| ADR-005 | Execution graph captured for every run by default, not opt-in | Accepted |

## ADR-001: Separate Planner and Router
**Context:** Task classification (what kind of work is needed) and tool/source selection (which specific tool/source) are logically distinct concerns.
**Decision:** Keep them as separate components with a `Plan` object as the interface between them.
**Consequences:** Routing strategy can evolve (new connectors, new source preferences) without retraining/changing task classification, and vice versa. See [../module-specs/PLANNER_SPEC.md](../module-specs/PLANNER_SPEC.md) and [../module-specs/ROUTER_SPEC.md](../module-specs/ROUTER_SPEC.md).

## ADR-002: Memory before Graph
**Context:** Graph updates depend on extracted, normalized content; re-extracting unchanged content to feed the graph is wasteful.
**Decision:** Memory's reuse/diff check happens before content is handed to Graph updates.
**Consequences:** Graph updates only process genuinely new/changed content, reducing cost. See [../architecture/DATA_FLOW.md](../architecture/DATA_FLOW.md).

## ADR-003: Outcome-first primary surface
**Context:** See [docs/concepts/outcomes-over-tools.md](../../docs/concepts/outcomes-over-tools.md).
**Decision:** `solve`/`observe` are the primary, most-documented surface; low-level primitives remain available but secondary.
**Consequences:** Most integration effort and documentation investment goes toward the outcome-first path; low-level primitives get a thinner but still complete spec ([../module-specs/](../module-specs/)).

## ADR-004: Content-addressed snapshot storage
**Context:** Historical replay and diffing require reliable, immutable point-in-time records.
**Decision:** Snapshots are stored by content hash rather than mutated in place.
**Consequences:** Simplifies diffing (compare two hashes) and dedup (identical content across targets shares storage); slightly higher storage overhead than in-place mutation. See [../data/STORAGE_SPEC.md](../data/STORAGE_SPEC.md).

## ADR-005: Execution graph captured by default
**Context:** Explainability is a core requirement, not an add-on (see [docs/concepts/explainability.md](../../docs/concepts/explainability.md)).
**Decision:** Every run captures a full trace by default; there is no "fast path" that skips tracing.
**Consequences:** Slight overhead on every run, accepted as a cost of the platform's core trust guarantee.
