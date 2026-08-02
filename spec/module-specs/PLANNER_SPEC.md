# Planner Spec

## Purpose
Classify task intent and produce an executable plan. See [docs/core/planner.md](../../docs/core/planner.md) for the conceptual overview.

## Interface
```
plan(task: string, mode?: Mode, skill?: string) -> Plan
```

## Plan object
```json
{ "id": "plan_abc", "steps": [{ "type": "search", "params": {...} }], "estimated_mode": "focus" }
```

## Algorithm (summary)
1. Match task against known [Skills](SKILLS_SPEC.md) templates; if matched, use the skill's plan template.
2. Otherwise, classify intent (lookup / comparison / monitoring / longitudinal) via task classification model.
3. Estimate required depth (source count, browsing needs) and set `estimated_mode` if not explicitly provided.
4. Emit step sequence for the [Router](ROUTER_SPEC.md).

## Failure modes
No matching skill and low-confidence classification → default to a conservative `focus`-equivalent plan rather than failing. See [../resilience/EDGE_CASES.md](../resilience/EDGE_CASES.md).

## Testing
See [../testing/UNIT_TESTS.md](../testing/UNIT_TESTS.md) for classification accuracy test requirements.
