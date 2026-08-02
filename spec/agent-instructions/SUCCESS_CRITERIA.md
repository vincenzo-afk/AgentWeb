# Success Criteria

## Per-phase success criteria (for an implementing agent to self-check against)

**Phase 0 (MVP)**
- `/solve` returns a cited answer for a representative task set with citation coverage meeting [../product/SUCCESS_METRICS.md](../product/SUCCESS_METRICS.md).
- `/observe` correctly detects an intentional change in a controlled test scenario ([../testing/SYSTEM_TESTS.md](../testing/SYSTEM_TESTS.md)).
- All [Phase 0 acceptance criteria](../testing/ACCEPTANCE_CRITERIA.md) pass.

**Phase 1 (Depth & Modes)**
- All four retrieval modes produce measurably different evidence depth on the same task, within [performance targets](../testing/PERFORMANCE_TARGETS.md).
- Browser escalation correctly triggers on JS-dependent fixture pages and does not trigger unnecessarily on static ones.

**Phase 2 (Memory & Graph)**
- Graph queries correctly answer a curated set of multi-hop relationship questions against fixture data.

**Phase 3 (Agent-Native)**
- A reference agent ([examples/research-agent](../../examples/research-agent)) can plan, inspect, and execute a multi-step task using only the Agent APIs.

## Global success criterion
No phase is "successful" if it violates any [invariant](../decisions/INVARIANTS.md) or fails [QUALITY_GATES.md](../testing/QUALITY_GATES.md), regardless of functional test results.
