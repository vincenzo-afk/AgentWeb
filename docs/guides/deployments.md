# Deployments

Guidance for integrating AgentWeb into your application's deployment topology.

## Direct API usage

For most applications, calling the AgentWeb API directly from your backend (never from client-side code, to protect API keys — see [security/secrets-management.md](../security/secrets-management.md)) is sufficient.

## Async / long-running tasks

`dive` mode and monitors are inherently asynchronous. Use `webhook_url` rather than polling for anything beyond quick `flash`/`focus` calls, to avoid holding open connections and to handle retries gracefully. See [api/webhooks.md](../api/webhooks.md).

## Scaling considerations

- Batch related lookups into fewer, broader tasks where possible rather than many narrow calls — this lets the planner reuse memory and sources across the batch.
- Watch [rate limits](../api/rate-limits.md) and configure backoff.
- For high monitor volume, review [operations/cost-controls.md](../operations/cost-controls.md).

## Environments

Use test keys (`sk-test-...`) in staging/CI to avoid billed usage and to exercise error paths safely.
