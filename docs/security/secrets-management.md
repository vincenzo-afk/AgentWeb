# Secrets Management

## API keys

- Store keys in environment variables or a secrets manager — never in source control or client-side code.
- Use scoped keys (see [api/authentication.md](../api/authentication.md)) so a compromised key has limited blast radius.
- Rotate keys periodically and immediately after any suspected exposure; AgentWeb supports multiple concurrent active keys to make rotation zero-downtime.

## Webhook signing secrets

- Treat the webhook signing secret with the same care as an API key.
- Verify the `X-AgentWeb-Signature` header on every incoming webhook before processing; see [api/webhooks.md](../api/webhooks.md).

## Credentials passed to browser workflows

If a [browser workflow](../guides/using-browser-workflows.md) needs to authenticate against a target site on your behalf, pass credentials via the dedicated secure credential mechanism rather than embedding them in `actions` payloads or task descriptions, so they aren't captured in logs or execution graphs.
