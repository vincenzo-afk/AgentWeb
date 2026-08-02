# Browser Engine

The browser layer enables rendering, interaction, navigation, and extraction from JavaScript-heavy or user-flow-dependent pages, where static fetches are insufficient. It is treated as core infrastructure, not an afterthought — consistent with the broader market trend of agent infrastructure platforms combining browser sessions, search, and fetch for human-like web interaction.

## Capabilities

- Full page rendering (JS execution)
- Interaction primitives: click, type, scroll, wait-for-selector
- Multi-step navigation flows
- Screenshot/DOM-based extraction hooks (feeds into [Extraction](extraction.md))

## Isolation

Each browser session runs sandboxed per request; see [security/sandboxing.md](../security/sandboxing.md) for the isolation model and [security/threat-model.md](../security/threat-model.md) for the risks this mitigates (arbitrary third-party JS execution).

## When the router chooses browser vs. static fetch

The [Router](router.md) prefers a static fetch when possible (cheaper, faster) and escalates to a browser session when a page requires JS rendering, login/interaction flows, or dynamic content that a static fetch would miss. See [guides/using-browser-workflows.md](../guides/using-browser-workflows.md).
