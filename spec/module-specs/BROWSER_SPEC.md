# Browser Spec

## Purpose

Rendered, interactive page access for JS-heavy or flow-dependent pages. See [docs/core/browser-engine.md](../../docs/core/browser-engine.md).

## Interface

```text
browser.open(url: string, actions: Action[], credential_id?: string) -> BrowserSession
```

Authenticated flows use a tenant-scoped opaque `credential_id` created through the admin credential endpoint. The credential secret is encrypted at rest with the provider-backed `AGENTWEB_BROWSER_CREDENTIAL_KEY`, resolved only for the isolated session, and scrubbed from output, traces, and errors. The only credential action is `fill_credential`, with `field` set to `username` or `secret`; raw credential values are rejected in actions.

## Process isolation

Each session is dispatched through a bounded, lazily created spawned worker process by default. The process pool is capped at eight workers and recycles workers after a bounded task count. A worker timeout terminates and replaces the pool, returning a retryable browser timeout. Typed `BrowserUnavailableError` and `BrowserActionError` outcomes are preserved across the worker boundary. `AGENTWEB_BROWSER_PROCESS_WORKERS=0` explicitly selects the direct in-process path for constrained local environments. No cookies, browser storage, credentials, or authenticated session state are persisted between requests.

## Escalation criteria (Router → Browser)

- Static fetch returns content that doesn't match expected schema/structure.
- Target domain is known (via [Connector](CONNECTOR_SPEC.md)) to require rendering.
- Task explicitly requires interaction (login, multi-step form, pagination click-through).

## Sandboxing requirements

Each session is isolated per request and resource-limited; network egress is restricted to the session target and same-origin resources. See [../security/SECURITY_MODEL.md](../security/SECURITY_MODEL.md) and [docs/security/sandboxing.md](../../docs/security/sandboxing.md).

Authorized operators may create encrypted Playwright-compatible storage state through the tenant-scoped session-state lifecycle endpoints. Each state is bound to one normalized HTTP(S) origin, stored with the provider-backed Fernet key, and exposed only through metadata. Browser execution may supply an opaque `session_state_id` for the same organization and origin; revoked, cross-tenant, cross-origin, malformed, and oversized states are rejected. Cookies, local storage, and session tokens never appear in browser results, traces, audit metadata, or list responses. `DELETE /admin/data` supports `kind: session_states` for organization cleanup.

## Failure modes

Selector not found / timeout → retry per [../resilience/TIMEOUT_POLICY.md](../resilience/TIMEOUT_POLICY.md); surface partial results if some actions succeeded. Session-state decryption or browser-context failures remain typed browser errors and do not fall back to an unauthenticated context. A worker-process failure remains retryable, while CAPTCHA/MFA automation remains a non-goal.
