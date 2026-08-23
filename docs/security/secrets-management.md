# Secrets Management

## API keys

- Store keys in environment variables or a secrets manager — never in source control or client-side code.
- Use scoped keys (see [api/authentication.md](../api/authentication.md)) so a compromised key has limited blast radius.
- Persistent customer keys are stored as PBKDF2-derived hashes in the relational store. The plaintext secret is returned only at creation time and is never written to traces, logs, or migration diagnostics.
- Rotate keys periodically and immediately after any suspected exposure; AgentWeb supports multiple concurrent active keys to make rotation zero-downtime.

## Platform secret providers

In development, the `env` provider is available for local compatibility. In staging and production, `AGENTWEB_SECRET_PROVIDER=env` is rejected. Use an approved deployment-backed provider or the command provider, configured with `AGENTWEB_SECRET_COMMAND`; it receives a validated secret name such as `DATABASE_URL` and returns only that value. Provider output is kept in a bounded in-process cache and is never serialized or included in error messages. `AGENTWEB_ENV`, `DATABASE_URL`, and other platform secrets must be sourced from the provider boundary before the application starts.

## Webhook signing secrets

- Treat the webhook signing secret with the same care as an API key.
- Verify the `X-AgentWeb-Signature` header on every incoming webhook before processing; see [api/webhooks.md](../api/webhooks.md).

## Credentials passed to browser workflows

If a [browser workflow](../guides/using-browser-workflows.md) needs to authenticate against a target site on your behalf, pass credentials via the dedicated secure credential mechanism rather than embedding them in `actions` payloads or task descriptions, so they aren't captured in logs or execution graphs.
