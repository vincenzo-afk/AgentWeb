# Sandboxing

## Browser session isolation

Each [browser session](../core/browser-engine.md) runs in an isolated environment per request:

- No shared browser state (cookies, storage, cache) across unrelated requests/organizations.
- Resource limits (CPU, memory, execution time) to bound the impact of adversarial or misbehaving pages.
- Network egress from within a browser session is restricted to the requested target and its same-origin resources where feasible, reducing lateral-movement risk from a malicious page.

## Extraction sandboxing

Structured extraction ([core/extraction.md](../core/extraction.md)) operates on captured page content rather than executing arbitrary code from the page beyond what's needed for rendering, limiting the attack surface of the extraction step itself.

## Why this matters

Because AgentWeb routinely visits URLs it doesn't control, sandboxing is the primary control against the [threat model's](threat-model.md) "arbitrary third-party page execution" risk category.
