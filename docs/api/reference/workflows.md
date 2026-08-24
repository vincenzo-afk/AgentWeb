# Event-driven workflows

AgentWeb can execute a bounded grounded-research task when a meaningful monitor event occurs. This is an opt-in trigger beyond webhook delivery: the workflow renders a user-supplied task template, calls the normal `/solve` path, and records the resulting execution ID or failure status.

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

Workflow definitions are tenant-scoped and require `workflow:manage`. Supported events are `monitor.change_detected` and `monitor.no_change`; the default is `monitor.change_detected`. The task template is bounded to 2,000 characters and supports `{event}`, `{monitor_id}`, `{target}`, `{from_hash}`, `{to_hash}`, and `{timestamp}`.

## Inspect definitions and runs

```http
GET /v1/workflows?limit=50
GET /v1/workflows/runs?limit=50
```

Runs are stored with `running`, `succeeded`, or `failed` status. The run record contains the opaque solve execution ID when available and a bounded error string on failure. Raw page content, credentials, and rendered task inputs are not included in run records.

Workflow execution is currently synchronous at the monitor-check boundary and uses the existing local solve implementation. Queued/distributed workers, richer event sources, operator controls, and external workflow integrations remain future deployment work.
