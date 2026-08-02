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

See [security/data-privacy.md](../security/data-privacy.md) for handling considerations if delivered content includes third-party page data.
