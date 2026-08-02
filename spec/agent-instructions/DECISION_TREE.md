# Decision Tree

For when the spec doesn't give a direct answer:

```
Does this touch an INVARIANT (../decisions/INVARIANTS.md)?
  YES → do not proceed with any option that violates it. Stop and flag.
  NO  ↓

Is this decision already covered by an existing ADR (../decisions/ARCHITECTURE_DECISIONS.md)?
  YES → follow the ADR.
  NO  ↓

Does PROJECT_SCOPE.md / NON_GOALS.md (../product/) rule this in or out?
  IN SCOPE  → proceed.
  OUT OF SCOPE → do not build it; note the request in DECISION_HISTORY.md for human review.
  UNCLEAR ↓

Is there a documented FALLBACK or DEFAULT behavior (../resilience/FALLBACKS.md, ../config/DEFAULTS.md)?
  YES → use it.
  NO  ↓

Choose the option most consistent with MANIFESTO.md principles
(outcome-first, grounded, explainable, memory-first),
record the choice + rationale in DECISION_HISTORY.md,
and flag for human review before it ships.
```
