# Webhooks

Webhooks deliver asynchronous results — primarily monitor alerts from `internet.observe()`, and optionally completion notifications for long-running `dive` tasks.

## Setup

```json
{
  "task": "Track visa slot availability and alert when a new slot appears",
  "webhook_url": "https://myapp.example.com/webhooks/agentweb"
}
```

## Payload

```json
{
  "event": "monitor.change_detected",
  "execution_id": "mon_abc123",
  "diff": { "summary": "New slot appeared for August", "changed_fields": ["availability"] },
  "timestamp": "2026-07-31T12:00:00Z"
}
```

## Verification

Each webhook request includes a signature header (`X-AgentWeb-Signature`) computed over the raw payload using your webhook signing secret. Verify this before trusting the payload, and reject requests with a stale timestamp to guard against replay.

Delivery is asynchronous: monitor changes enqueue a tenant-scoped `webhook_delivery` job rather than blocking the monitor check on network delivery. The worker performs one outbound attempt per queue lease, records each attempt without storing the signing secret, retries transient failures with bounded backoff for at most five attempts, and moves exhausted work to `dead_letter`. Delivery is rate-limited per organization; a `rate_limited` state is retried by the queue. Poll `GET /observe/{id}` to inspect `last_delivery_status`, `last_delivery_attempts`, and the latest redacted error. A successful attempt is recorded before the job is acknowledged so a worker retry does not resend an already successful delivery.

See [security/data-privacy.md](../security/data-privacy.md) for handling considerations if delivered content includes third-party page data.
