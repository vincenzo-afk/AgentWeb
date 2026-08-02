# Building Connectors

Connectors extend AgentWeb's [Router](../core/router.md) with knowledge of a specific source or site family (e.g., a particular ecommerce platform's page structure, or a documentation platform's navigation pattern), improving extraction accuracy and reducing wasted browsing.

## When to build a connector

- You repeatedly target the same site/platform and generic extraction misses fields.
- A site has a login flow or interaction pattern generic browsing doesn't handle well.
- You want to bias routing toward/away from specific sources for your domain.

## Steps

1. Define the target pattern (URL structure or site family).
2. Provide extraction hints (selectors, expected schema) — see [core/extraction.md](../core/extraction.md).
3. Optionally provide a browser interaction script for login/navigation flows — see [core/browser-engine.md](../core/browser-engine.md).
4. Register the connector and test against representative URLs.

Connectors compose with [Internet Skills](../concepts/internet-skills.md) — a skill can be defined to prefer a specific connector for a given task class.
