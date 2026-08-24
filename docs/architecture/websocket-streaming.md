# WebSocket Streaming Server Architecture

## 1. Executive recommendation

AgentWeb should add WebSocket streaming as an **optional event-delivery plane** beside the existing REST API and signed webhook system. REST remains the command and query plane: it creates or starts work, returns the `execution_id`, and exposes the durable report and replay projections. WebSockets provide low-latency observation of an execution while it is running. Webhooks remain the durable external notification mechanism for monitor changes.

The first implementation should be a separate, optional streaming process rather than an upgrade bolted onto the dependency-free `ThreadingHTTPServer`. The current API server can continue to serve REST and webhooks unchanged, while an ASGI/WebSocket gateway reads the same tenant-scoped event journal and subscribes to a process-local publisher or a later shared broker. A reverse proxy can expose both services under the same public origin:

```text
                     HTTPS / WSS
                          |
                 TLS-terminating proxy
                    /               \
                   /                 \
       REST /v1/* API                 WebSocket /v1/stream
       ThreadingHTTPServer             Streaming gateway
                   \                 /
                    \               /
               SQLite event journal + execution traces
                          |
                    AgentWeb engine
```

This preserves the repository’s local-first boundary and avoids introducing a second source of truth. The execution trace remains the durable record of the run; the event journal is an ordered delivery log for live consumers and short-window replay.

## 2. Existing contract and compatibility boundary

The existing WebSocket specification defines the connection shape `wss://api.agentweb.dev/v1/stream?execution_id={id}` and five server message types: `plan_ready`, `source_found`, `partial_answer`, `complete`, and `error`. The design below keeps those message types and adds a versioned envelope around them. Clients that only inspect `type` remain forward-compatible, while clients that need reliable resume use `event_id`, `sequence`, and `execution_id`.

The stream is optional. The existing synchronous REST behavior, `dive`-mode webhook behavior, `/report/{execution_id}`, and `/report/{execution_id}/replay` continue to work when the streaming gateway is disabled. A stream disconnect must never cancel an execution, suppress trace persistence, alter synthesis, or change webhook delivery.

## 3. Logical components

| Component | Responsibility | Initial placement | Durable state |
|---|---|---|---|
| `ExecutionEvent` | Validated event model with type, sequence, execution, tenant, timestamp, and bounded payload | Shared Python package | No |
| `ExecutionEventJournal` | Append-only ordered records and bounded retention | SQLite beside `MemoryStore` | Yes |
| `ExecutionEventBus` | Low-latency in-process fan-out to active subscribers | API/worker process | No; journal is fallback |
| `StreamGateway` | WebSocket upgrade, handshake authentication, authorization, replay, flow control, and close semantics | Separate optional process | No |
| `ExecutionPublisher` | Publishes engine lifecycle events to the journal before notifying subscribers | Engine runtime | Uses journal |
| `StreamTicketService` | Optional short-lived browser ticket minted over authenticated REST | REST API | Short-lived hashed ticket or existing key store extension |
| `StreamMetrics` | Connection, delivery, replay, backpressure, and terminal-event metrics | Gateway and shared metrics boundary | Existing metrics store |

The `ExecutionEventJournal` should use an append-only table with a uniqueness constraint on `(execution_id, sequence)` and an index on `(org_id, execution_id, sequence)`. Payloads must be JSON objects validated against bounded per-event schemas. Journal retention should be materially shorter than trace retention, such as 15–60 minutes after a terminal event, unless a deployment explicitly requires longer replay.

## 4. Event lifecycle

Every event follows the same ordering rule: **validate, persist, then publish**. If publication fails after persistence, a reconnecting client can recover from the journal. If persistence fails, the engine must record a bounded error in the execution trace and continue using the existing REST failure behavior; it must not claim that an event was delivered.

A normal `dive` execution follows this sequence:

| Sequence | Type | Producer | Required payload | Replayability |
|---:|---|---|---|---|
| 1 | `plan_ready` | Planner/router | Bounded plan summary and estimated mode | Reliable |
| 2..N | `source_found` | Fetch/search/browser adapters | Source ID, redacted URL, title, trust/confidence metadata | Reliable |
| N+1..M | `partial_answer` | Synthesis stage | Bounded `text_delta` and optional `part_index` | Best-effort or coalesced |
| M+1 | `complete` | Solve finalizer | Final result summary or result reference | Reliable terminal |

Any unrecoverable failure produces one `error` event with a typed, redacted error object. The gateway then closes with a normal application-level terminal state, not a transport failure, so clients can distinguish “the run failed” from “the socket broke.” A cancellation or server shutdown should use a separate internal terminal reason and must not be represented as a successful `complete` event.

The publisher must not emit raw page bodies, browser credentials, API keys, webhook signing material, or unrestricted synthesis context. `source_found` carries the same redacted source metadata already suitable for trace/report output. `partial_answer` carries only bounded synthesis deltas; clients can fetch the authoritative final result through REST after `complete`.

## 5. Message protocol

### 5.1 Server-to-client envelope

The existing event types remain top-level and are supplemented with common fields:

```json
{
  "schema_version": 1,
  "type": "source_found",
  "event_id": "evt_01J...",
  "execution_id": "exec_abc123",
  "sequence": 2,
  "occurred_at": "2026-08-25T12:00:01.125Z",
  "replayable": true,
  "source": {
    "id": "src_abc",
    "url": "https://example.com/article",
    "title": "Example article",
    "trust_score": 0.91,
    "extraction_confidence": 0.84
  }
}
```

The required event-specific shapes remain compatible with the current specification:

```json
{ "type": "plan_ready", "plan": { "mode": "dive", "steps": [] } }
{ "type": "source_found", "source": { "id": "src_abc", "url": "https://example.com" } }
{ "type": "partial_answer", "text_delta": "The first supported finding is..." }
{ "type": "complete", "result": { "execution_id": "exec_abc123" } }
{ "type": "error", "error": { "type": "upstream_error", "message": "source unavailable" } }
```

All payload sizes should be bounded. A proposed initial limit is 64 KiB per message and 1 MiB total replay per connection. Oversized source or result fields are replaced with references or truncated summaries, never silently emitted as raw content.

### 5.2 Connection and resume

The initial URL remains:

```text
wss://api.agentweb.dev/v1/stream?execution_id=exec_abc123
```

A client may send an optional resume control message immediately after the handshake:

```json
{ "type": "resume", "after_sequence": 7 }
```

The server replays events with `sequence > 7`, then switches to live delivery. The server should also accept `Last-Event-Sequence: 7` during the upgrade for non-browser clients. If the requested sequence is older than journal retention, the server sends an `error` with `type: "stream_cursor_expired"` and includes the authoritative REST report URL; it must not pretend the stream is complete.

Acknowledgements are optional in the first version because the journal provides replay. For long-lived or high-value streams, the client may send:

```json
{ "type": "ack", "sequence": 12 }
```

Acknowledgements are telemetry and flow-control hints, not proof that a terminal result is durably processed. The client remains responsible for deduplicating by `event_id` or `(execution_id, sequence)`.

### 5.3 Completion and close behavior

The server sends exactly one terminal event, either `complete` or `error`, for an execution that reaches a terminal state. It then waits for an optional short acknowledgement window or closes after a bounded drain timeout with WebSocket close code `1000`. A transport close before the terminal event is non-terminal from the execution’s perspective; reconnect and resume are expected.

## 6. Authentication and tenant isolation

The stream must use the same bearer-key identity model as REST and must add a dedicated `stream:read` scope to avoid granting live execution visibility accidentally. `admin:*` may satisfy the scope as it does for other endpoints, but it does not bypass organization ownership checks.

For server-to-server clients, authenticate the upgrade with `Authorization: Bearer ...`. Browser clients cannot reliably set that header through the native WebSocket constructor, so the REST API should optionally mint a **short-lived, single-use stream ticket** after normal bearer authentication. The ticket is presented through a subprotocol or a secure, short-lived cookie; it must not be a long-lived API key in the query string. Query parameters are limited to `execution_id` and non-secret resume metadata.

The handshake sequence is:

1. Parse and validate `execution_id` and reject malformed identifiers before opening a socket.
2. Authenticate the bearer key or single-use ticket.
3. Resolve the execution trace or event-journal ownership using `(org_id, execution_id)`.
4. Return a generic not-found or unauthorized response for cross-tenant and unknown executions to avoid an execution-ID oracle.
5. Apply per-organization connection and replay limits.
6. Subscribe only to the authorized execution ID.

Revocation and long-lived connections require a policy decision. The safe default is to revalidate the principal at a bounded interval, such as every five minutes, and immediately stop delivery when the key is revoked. Origin allowlisting, TLS termination, maximum frame sizes, idle timeouts, and per-organization connection quotas are mandatory deployment controls.

## 7. Reliability and backpressure

The delivery contract should be **at least once, ordered per execution, and resumable**, not exactly once. Exactly-once delivery across a WebSocket and a reconnecting client is not realistic; sequence numbers and client deduplication provide the useful guarantee.

| Condition | Required behavior |
|---|---|
| Subscriber connects during a run | Replay retained events, then subscribe to live events without a sequence gap |
| Subscriber reconnects | Resume after a sequence or receive cursor-expired guidance |
| Slow client | Bound the outbound queue; coalesce or drop non-terminal partial deltas while retaining source and terminal events |
| Journal write succeeds but socket publish fails | Keep the journal record; reconnecting clients recover it |
| Journal is unavailable | Continue existing execution semantics, record a trace warning, and expose a degraded stream error rather than claiming delivery |
| Gateway restarts | No execution is cancelled; clients reconnect and resume from the journal |
| Duplicate event observed | Client ignores a previously processed `event_id` or sequence |
| Process crashes before persistence | Event may be absent; the final trace/report remains authoritative |

The gateway should maintain separate queues for reliable events and partial deltas. Reliable queues must never be displaced by partial output. A per-connection queue limit, a global connection limit, and an organization-level bandwidth budget prevent one tenant or client from exhausting the process.

## 8. Runtime integration points

The engine should publish at four explicit boundaries rather than exposing internal mutable objects:

1. After planner and router selection, publish a sanitized `plan_ready` summary.
2. When an accepted source enters the candidate set, publish a sanitized `source_found` record.
3. When synthesis produces a bounded delta, publish `partial_answer`; a coalescing adapter may combine adjacent deltas before journaling.
4. In the finalization block, publish exactly one `complete` or `error` terminal event after the trace status is determined.

The publisher should receive `org_id` and `execution_id` explicitly on every call. It must not infer tenant identity from a connection or global state. Existing `TraceStore` persistence remains independent and should be updated at the same lifecycle boundaries so `/report` and streaming do not diverge in status.

The monitor and workflow systems should not be coupled to this execution stream in the first release. Monitor events continue to use the existing durable workflow queue and signed webhooks. A future stream may expose monitor/workflow status through a separate subscription model, but that would require a new topic authorization contract and should not be mixed into execution stream semantics.

## 9. Deployment topology

### Local-first single process

The first useful deployment can run the REST API, engine, event journal, and an in-process event bus together, with the WebSocket gateway as an optional process reading the same SQLite journal. SQLite should use WAL mode and a busy timeout for concurrent REST/gateway access. This mode is suitable for development and single-node deployments only.

### Multi-node deployment

For multiple API and gateway instances, the journal remains the recovery source, but a shared notification mechanism is needed for low latency. The preferred sequence is:

1. Append the event in the authoritative relational/event journal transaction.
2. Publish a lightweight notification containing only `org_id`, `execution_id`, and `sequence`.
3. The gateway receiving the notification reads the event by key, rechecks tenant authorization, and sends the sanitized record.
4. If the notification is lost, a bounded poller or reconnect replay finds the journal record.

The existing PostgreSQL coordinator can be considered for notification and lease coordination, but it is not currently a general pub/sub contract. Do not claim multi-node streaming readiness until the deployment chooses and load-tests a notification/broker mechanism.

## 10. Observability and operations

The streaming gateway should emit structured logs with `request_id`, `execution_id`, `org_id` only where policy permits, `component: "stream"`, connection state, event type, sequence, and bounded latency. It must never log bearer tokens, stream tickets, raw page bodies, or full synthesis context.

Recommended metrics include:

| Metric | Dimensions | Purpose |
|---|---|---|
| `stream_connections_active` | organization bucket, gateway instance | Capacity and abuse detection |
| `stream_handshakes_total` | result, auth outcome | Authentication and client health |
| `stream_events_published_total` | event type, result | Publisher health |
| `stream_events_delivered_total` | event type, replay/live | Delivery health |
| `stream_replay_lag` | event sequence distance | Recovery performance |
| `stream_backpressure_total` | event type, close reason | Slow-client detection |
| `stream_cursor_expired_total` | deployment | Journal retention sizing |
| `stream_terminal_latency_seconds` | mode, result | End-to-end experience |

Health checks should distinguish “REST healthy, streaming disabled” from “streaming enabled but journal/gateway degraded.” A stream gateway failure must not make the REST health endpoint claim that the execution engine is unavailable unless the configured deployment treats streaming as mandatory.

## 11. Testing strategy

The implementation should be accepted only when the following test groups pass:

| Test group | Required assertions |
|---|---|
| Event model | Allowed types, required fields, monotonic sequence, payload bounds, redaction, schema version |
| Journal | Tenant isolation, unique sequence, ordered replay, retention, cursor expiry, concurrent append behavior |
| Publisher | Persist-before-publish ordering, one terminal event, no raw content, trace status alignment |
| Handshake | Valid bearer scope, invalid token, revoked token, unknown execution, cross-tenant execution, malformed ID, origin policy |
| Resume | Replay from sequence, duplicate-free client behavior, cursor expiry guidance, live handoff without gaps |
| Backpressure | Partial coalescing/drop policy, reliable event retention, queue bounds, slow-client close |
| Failure recovery | Gateway restart, journal outage, publisher failure, worker crash, client reconnect |
| Integration | `dive` execution emits the documented sequence while REST report/replay and webhooks remain unchanged |
| Operations | Structured log redaction, metrics, health degradation, connection quotas, `LOG_LEVEL` filtering |

A deterministic fake publisher and in-memory journal can cover protocol behavior without making network calls. At least one real WebSocket integration test should exercise the optional gateway when the streaming dependency is installed.

## 12. Phased implementation plan

| Phase | Scope | Exit criteria |
|---|---|---|
| A — Contract and models | Finalize envelope, `stream:read`, ticket rules, event schemas, retention, and error codes | Versioned spec approved; no REST behavior changes |
| B — Single-node delivery | Add journal, publisher hooks, optional WebSocket gateway, replay, and basic limits | `dive` emits ordered events; reconnect recovers retained events;  tenant isolation passes |
| C — Browser and operator ergonomics | Add short-lived browser tickets, client SDK guidance, health/metrics, and structured stream logs | No long-lived tokens in URLs; operational dashboards and redaction tests pass |
| D — Distributed delivery | Add shared notification/broker integration and multi-node recovery testing | Lost notifications recover by journal polling; load and failover tests pass |
| E — Broader topics | Consider monitor/workflow topics only under a separate authorization and retention contract | Separate topic specification and threat model approved |

Phase B should remain behind `websocket_streaming_enabled` and an explicit deployment configuration. It should be possible to run the entire repository without installing the optional WebSocket dependency.

## 13. Decisions and non-decisions

This design deliberately chooses an **optional separate gateway**, a **durable short-window journal**, **at-least-once ordered delivery**, **tenant-bound handshake authorization**, and **REST/webhook compatibility**. It deliberately does not choose a specific hosted broker, a public client SDK, a monitor-topic protocol, exactly-once semantics, or a full relational runtime cutover. Those decisions depend on deployment topology, traffic limits, and an approved production evaluation plan.

> The WebSocket stream is a live view of an execution, not a new system of record. The persisted execution trace and final REST report remain authoritative.

## References

1. [AgentWeb WebSocket API specification](../../spec/api/WEBSOCKET_API.md)
2. [AgentWeb REST API specification](../../spec/api/REST_API.md)
3. [AgentWeb authentication scopes and principals](../../src/agentweb/auth.py)
4. [AgentWeb execution trace persistence](../../src/agentweb/trace.py)
5. [AgentWeb execution engine](../../src/agentweb/engine.py)
6. [AgentWeb structured logging contract](../../spec/observability/LOGGING.md)
