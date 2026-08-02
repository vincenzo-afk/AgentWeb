# Agent Guide

This document orients an AI coding agent tasked with implementing AgentWeb from this spec tree.

## Read order
1. [../product/VISION.md](../product/VISION.md) and [../product/PRODUCT_SPEC.md](../product/PRODUCT_SPEC.md) — what and why.
2. [../architecture/SYSTEM_OVERVIEW.md](../architecture/SYSTEM_OVERVIEW.md) and [../architecture/HIGH_LEVEL_DESIGN.md](../architecture/HIGH_LEVEL_DESIGN.md) — how the pieces fit.
3. [../build-plan/BUILD_ORDER.md](../build-plan/BUILD_ORDER.md) — what to build first.
4. The specific `*_SPEC.md` for whatever module you're implementing.
5. [../decisions/INVARIANTS.md](../decisions/INVARIANTS.md) and [../decisions/CONSTRAINTS.md](../decisions/CONSTRAINTS.md) — what you must never violate.
6. [../testing/DONE_DEFINITION.md](../testing/DONE_DEFINITION.md) — how you'll know you're finished.

## Ground rules
See [AGENT_RULES.md](AGENT_RULES.md) for hard constraints and [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md) for the expected working loop.

## If the spec is ambiguous or silent on something
Prefer the interpretation most consistent with [../product/MANIFESTO.md](../product/MANIFESTO.md) principles (outcome-first, grounded, explainable, memory-first). Record the interpretation and its rationale in [PROJECT_MEMORY.md](PROJECT_MEMORY.md) and [DECISION_HISTORY.md](DECISION_HISTORY.md) rather than silently choosing and moving on.
