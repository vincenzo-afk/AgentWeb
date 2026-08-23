# Data Privacy

## What AgentWeb stores

- **Snapshots** of publicly accessible third-party pages ([core/memory.md](../core/memory.md))
- **Extracted structured data** derived from those pages
- **Graph entities/relationships** derived from extraction across runs
- **Execution traces** of your organization's own tasks/runs
- **Task descriptions** you submit (which may reference your own business context)

## Organizational isolation

Snapshot, execution-trace, task, monitor-job, API-key, and audit-event data are scoped to the owning organization. Ownership is checked on every read, update, delete, trace lookup, and scheduled-job claim; a valid key from another organization receives a not-found result rather than a record-disclosure signal. Graph intelligence derived from public web content may be shared in aggregate (e.g., "this entity is a known competitor of that entity") without exposing which organization's task triggered the discovery, but organizations can opt out of contributing to shared graph intelligence — see your account settings.

## Third-party content caveats

Because AgentWeb's core function is browsing and extracting from third-party pages, stored snapshots may contain content AgentWeb does not own or control. Deletion requests for specific snapshots/targets are supported; see [operations/data-retention.md](../operations/data-retention.md).

## Compliance-sensitive use

For workflows involving regulated data categories, review [compliance-notes.md](compliance-notes.md) before relying on AgentWeb as part of a compliance-relevant process.
