# Building Connectors

Connectors extend AgentWeb’s [Router](../core/router.md) with knowledge of a specific source or site family. A connector can improve extraction accuracy, add a bounded browser interaction script, and bias ranking for a recurring source family.

## Register a connector

```python
from agentweb import AgentWebEngine, Connector

engine = AgentWebEngine()
engine.connectors.register(
    Connector(
        name="github-releases",
        pattern="https://github.com/org/repo/releases",
        extraction_hints={"published_at": "date", "title": "string"},
        interaction_script=[{"type": "wait_for", "selector": "main"}],
        ranking_bias={"boost": ["release"], "penalize": ["sponsored"]},
    )
)
```

The pattern may be a complete URL prefix or a hostname. Hostname patterns match the host and its subdomains. When multiple connectors match, the longest normalized pattern wins; ties are resolved by connector name. Duplicate connector names are rejected, and connector action lists are bounded to 20 entries.

## Runtime behavior

The router annotates matching `extract` and `browser` calls with the connector name. Extraction hints are applied to static fetches as bounded normalized fields, browser connectors supply their interaction script only when the caller has not provided actions, and ranking bias terms adjust only sources produced by the matching connector. Generic routing remains the fallback when no connector matches.

Connector registration is process-local by design. Applications should register connectors during startup and keep patterns narrow. Connector actions must remain authorized, same-origin, and free of raw credentials; the existing browser isolation and trust policy still applies.
