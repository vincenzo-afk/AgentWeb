# Browser Engine

The browser layer enables rendering, interaction, navigation, and extraction from JavaScript-heavy or user-flow-dependent pages, where static fetches are insufficient. It is treated as core infrastructure, not an afterthought — consistent with the broader market trend of agent infrastructure platforms combining browser sessions, search, and fetch for human-like web interaction.

## Capabilities

- Full page rendering with JavaScript execution.
- Interaction primitives: click, type, scroll, wait-for-selector, and credential-backed form filling.
- Multi-step navigation flows.
- Screenshot/DOM-based extraction hooks that feed into [Extraction](extraction.md).
- A bounded, lazily created spawned process pool for browser work, with worker recycling and explicit shutdown.

## Isolation

Each browser session creates a fresh context and executes in a bounded browser-worker process. The process boundary limits browser-runtime failures and prevents browser state from leaking between requests. HTTP(S) egress is restricted to the target origin and same-origin resources by default; see [security/sandboxing.md](../security/sandboxing.md) for the isolation model and [security/threat-model.md](../security/threat-model.md) for the risks this mitigates, including arbitrary third-party JavaScript execution.

Credentials are resolved only for the isolated session through an opaque tenant-scoped credential reference. Raw credential values are rejected in action payloads, and credential material is scrubbed from output, errors, and persisted traces. By default, cookies and browser storage are discarded with the fresh context. An authorized operator may explicitly create encrypted, origin-bound Playwright storage state through the session-state admin endpoints and supply its opaque `session_state_id` to a later request; state is resolved only for the same organization and origin and is never included in results.

## Process-pool configuration

The default `AGENTWEB_BROWSER_PROCESS_WORKERS=1` setting uses one spawned browser worker. The value is bounded to eight. Set it to `0` to use the direct in-process path for constrained local environments. The existing `AGENTWEB_BROWSER_WORKERS` semaphore continues to bound concurrent API requests independently of process count. Worker processes are created lazily, recycled after a bounded task count, terminated on session timeout, and closed when the engine is explicitly shut down.

## When the router chooses browser vs. static fetch

The [Router](router.md) prefers a static fetch when possible because it is cheaper and faster. The local planner escalates a bounded URL step to a browser when the task explicitly contains rendering or interaction intent such as `render`, `javascript`, `click`, `login`, `form`, `pagination`, or `browser`; ordinary direct-URL tasks continue to use static extraction. Optional `inputs.actions` are passed through only as the existing bounded browser actions. Optional `inputs.credential_id` and `inputs.session_state_id` remain opaque references resolved through the organization/origin checks already used by the direct browser endpoint. Invalid references fail closed and never fall back to an unauthenticated browser context. See [guides/using-browser-workflows.md](../guides/using-browser-workflows.md).
