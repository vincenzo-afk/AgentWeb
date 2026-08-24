# Building Plugins

AgentWeb plugins are process-local Python extensions registered during application startup. They generalize connector, skill, and ranking customization without loading customer-supplied code from the network. The registry is organization-scoped and every registration carries an explicit name and version.

## Register a plugin

```python
from agentweb import AgentWebEngine, Plugin

engine = AgentWebEngine()
engine.plugins.register(
    Plugin(
        name="release-ranker",
        version="1.0.0",
        org_id="org-acme",
        type="ranker",
        match=lambda context: "release" in context["task_context"].lower(),
        hooks={"score_override": lambda context: context["base_score"] + 0.05},
    )
)
```

The dictionary form accepted by `PluginRegistry.register` and `register_plugin` has the same fields: `name`, `version`, `org_id`, `type`, `match`, and `hooks`. Supported plugin types and hooks are summarized below.

| Type | Hooks | Runtime use |
|---|---|---|
| `connector` | `extraction_hints`, `interaction_script`, `ranking_bias` | Enrich matching URL extraction or browser calls after ordinary connector matching. |
| `skill` | `plan_template`, `input_schema` | Supply a bounded planning template when no built-in skill matches. |
| `ranker` | `score_override` | Replace a source's deterministic base score for the current organization and task. |

## Contract and safety behavior

A plugin match predicate receives a bounded context containing the current organization identifier and request-local values. A hook receives a defensive copy of its context. Match predicates and hooks are executed with a configurable timeout, defaulting to 100 milliseconds. Exceptions, invalid return values, and timeouts are ignored for that call, so the normal connector, planner, or ranking behavior remains the fallback.

Plugin registration is not a security boundary for arbitrary third-party code. The current implementation is intentionally process-local: operators must register reviewed code during startup and should not expose registration to untrusted tenants. Plugins must not perform network access, mutate shared state, or read data outside the organization in their current context. Existing trust, browser isolation, redaction, and tenant authorization controls continue to apply.

Plugin updates affect future calls only. Existing execution traces contain redacted summaries and are not recomputed when a plugin version changes. Duplicate `(org_id, name)` registrations are rejected, and listing or lookup always requires the organization scope.
