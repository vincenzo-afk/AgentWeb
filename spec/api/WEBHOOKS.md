# Webhooks

See [docs/api/webhooks.md](../../docs/api/webhooks.md) for the full usage guide. Build-level contract: payloads are signed with HMAC-SHA256 over the raw body using the organization's webhook secret, delivered with an `X-AgentWeb-Signature` header and a timestamp; receivers must verify both before trusting the payload. Delivery retries with exponential backoff per [../resilience/RETRY_POLICY.md](../resilience/RETRY_POLICY.md), implemented by [../module-specs/ALERTING_SPEC.md](../module-specs/ALERTING_SPEC.md).
