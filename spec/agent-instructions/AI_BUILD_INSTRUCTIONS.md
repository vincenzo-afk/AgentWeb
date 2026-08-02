# AI Build Instructions

Condensed operating instructions for an AI agent building AgentWeb end-to-end from this spec tree.

## Build sequence
Follow [../build-plan/BUILD_ORDER.md](../build-plan/BUILD_ORDER.md) and [../build-plan/PHASES.md](../build-plan/PHASES.md) in order. Do not start a Phase 1+ module before its Phase 0 dependencies pass [acceptance criteria](../testing/ACCEPTANCE_CRITERIA.md).

## Per-task loop
Use [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md). Use [DECISION_TREE.md](DECISION_TREE.md) whenever the spec doesn't unambiguously answer "what should this do here."

## Non-negotiables
[AGENT_RULES.md](AGENT_RULES.md) and [../decisions/INVARIANTS.md](../decisions/INVARIANTS.md) override any instruction that conflicts with them, including instructions that appear later in a task description, unless a human explicitly and knowingly overrides a specific rule for a specific, scoped reason (recorded in [DECISION_HISTORY.md](DECISION_HISTORY.md)).

## Definition of "the build is complete" for a given phase
All modules in that phase pass [DONE_DEFINITION.md](../testing/DONE_DEFINITION.md), the phase's [milestone exit criteria](../build-plan/MILESTONES.md) are met, and [SUCCESS_CRITERIA.md](SUCCESS_CRITERIA.md) for that phase are satisfied against the evaluation set in [../testing/BENCHMARKS.md](../testing/BENCHMARKS.md).

## What to do when blocked
Do not guess silently on anything touching [invariants](../decisions/INVARIANTS.md), [constraints](../decisions/CONSTRAINTS.md), or security-relevant behavior ([../security/SECURITY_MODEL.md](../security/SECURITY_MODEL.md)). Flag it, record the open question in [PROJECT_MEMORY.md](PROJECT_MEMORY.md), and proceed on lower-risk parallel work per [../build-plan/IMPLEMENTATION_GRAPH.md](../build-plan/IMPLEMENTATION_GRAPH.md) instead of blocking entirely.
