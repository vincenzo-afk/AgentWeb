# Alerting Spec

## Purpose
Deliver monitor change alerts and run-completion notifications. See [docs/api/webhooks.md](../../docs/api/webhooks.md).

## Interface
```
send_webhook(url: string, payload: object, signing_secret: string) -> DeliveryResult
```

## Behavior
- Signs payload with HMAC using the organization's webhook signing secret.
- Includes a timestamp to guard against replay.
- Retries with backoff on non-2xx response, up to a bounded window (see [../resilience/RETRY_POLICY.md](../resilience/RETRY_POLICY.md)).
- Failed deliveries beyond the retry window are surfaced via monitor status polling, not silently dropped.

## Rate limiting
Alert delivery is rate-limited per organization to avoid overwhelming a receiving endpoint during a burst of simultaneous changes.
