# Plugin System

## Purpose
Generalizes [Connectors](../module-specs/CONNECTOR_SPEC.md) and [Skills](../module-specs/SKILLS_SPEC.md) into a common extension mechanism, so future extension points (custom rankers, custom normalizers for a domain) can reuse the same registration/execution model.

## Registration model
Plugins register a `match` predicate (when do I apply) and one or more hook implementations (what do I do). The [Router](../module-specs/ROUTER_SPEC.md) and [Planner](../module-specs/PLANNER_SPEC.md) consult registered plugins before falling back to default behavior.

## Isolation
Plugin code (especially anything supplied by a customer, like [custom ranker](../../docs/guides/custom-rankers.md) logic) runs in a constrained execution context — no arbitrary network access, bounded execution time — consistent with [../security/SECURITY_MODEL.md](../security/SECURITY_MODEL.md).
