# Event-driven workflows

AgentWeb can execute a bounded grounded-research task when a meaningful monitor event occurs. This is an opt-in trigger beyond webhook delivery: the workflow records a durable `workflow_run` queue job, the supervised worker renders the user-supplied task template, calls the normal `/solve` path, and records the resulting execution ID or failure status.

## Register a workflow

```http
POST /v1/workflows
Content-Type: application/json
Idempotency-Key: workflow-setup-001

{
  "name": "Summarize product changes",
  "monitor_id": "mon_123",
  "event": "monitor.change_detected",
  "task_template": "Summarize the latest changes at {target}; previous snapshot {from_hash}, current snapshot {to_hash}.",
  "mode": "focus"
}
```

Workflow definitions are tenant-scoped and require `workflow:manage`. Supported events are `monitor.change_detected`, `monitor.no_change`, and `monitor.check_failed`; the default is `monitor.change_detected`. Monitor checks emit matching events, while webhook delivery remains change-only. Failure workflows receive the bounded `{error}` value in addition to the common monitor fields.
 The task template is bounded to 2,000 characters and supports `{event}`, `{monitor_id}`, `{target}`, `{from_hash}`, `{to_hash}`, `{timestamp}`, and `{error}`.

## Pause and resume

```http
POST /v1/workflows/pause
Content-Type: application/json
Idempotency-Key: workflow-pause-001

{"workflow_id": "wf_123"}
```

Use `POST /v1/workflows/resume` with the same payload to reactivate a paused definition. Paused workflows retain their definitions and historical runs but do not create new jobs for matching monitor events. Both controls require `workflow:manage` and are idempotent when an `Idempotency-Key` is supplied.

## Inspect definitions and runs

```http
GET /v1/workflows?limit=50
GET /v1/workflows/runs?limit=50
```

Runs are stored with `queued`, `running`, `succeeded`, or `failed` status. The run record contains the opaque solve execution ID when available and a bounded error string on failure. Raw page content, credentials, and rendered task inputs are not included in run records. Queue jobs use the existing scheduler lease, retry, rate-limit, and dead-letter behavior.

The current worker is local-first and supervised through `agentweb --worker`; the same queue contract can be backed by the explicitly enabled distributed coordinator. Richer event sources, operator controls, and external workflow integrations remain future deployment work.
