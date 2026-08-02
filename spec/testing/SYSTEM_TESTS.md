# System Tests

## Scope
Full pipeline (Planner → Router → Execution → Memory → Ranking → Synthesis) running against a controlled, self-hosted test-fixture website with known, stable content — not the live internet.

## Why a controlled fixture site
Enables deterministic assertions on citation accuracy, trust scoring, and synthesized answer content, which would be impossible against live, changing internet content.

## Key scenarios
- End-to-end `solve` call against fixture site produces a correctly cited answer matching expected content.
- End-to-end `observe` call detects an intentional content change made to the fixture site between two scheduled checks.
- Mode selection: verify `flash`/`focus`/`dive` produce measurably different depth of evidence gathering against the same fixture task.
