# WebSocket API

## Purpose
Optional real-time channel for streaming partial synthesis output and live execution-graph events during a `dive`-mode run, as an alternative to polling or waiting for a webhook.

## Connection
```
wss://api.agentweb.dev/v1/stream?execution_id={id}
```

## Message types
```json
{ "type": "plan_ready", "plan": {...} }
{ "type": "source_found", "source": {...} }
{ "type": "partial_answer", "text_delta": "..." }
{ "type": "complete", "result": {...} }
{ "type": "error", "error": {...} }
```

## Status
Not required for MVP; the REST + webhook model ([REST_API.md](REST_API.md), [WEBHOOKS.md](WEBHOOKS.md)) covers Phase 0/1 needs. Scheduled for consideration alongside [docs/roadmap.md](../../docs/roadmap.md) Phase 1 depth improvements, for clients that want live progress rather than a final result only.
