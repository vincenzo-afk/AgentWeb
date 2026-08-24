# Data Retention

## Retained data types

| Data | Default retention | Notes |
|---|---|---|
| Snapshots ([Memory](../core/memory.md)) | 90 days | Longer retention available for audit/compliance use cases |
| Crawl runs and page metadata | 90 days | Crawl pages are removed with their owning run; the window is configurable through `agentweb gc --crawl-days` |
| Execution graphs/traces | 30 days | Needed for [debugging](../getting-started/debugging-basics.md) and replay |
| Idempotency keys | 24 hours | See [api/idempotency.md](../api/idempotency.md) |
| API usage/billing records | 24 months | For account history and invoicing |
| Security audit events | 730 days | Local default; configurable through `agentweb gc --audit-days`, with optional organization scoping |
| Graph entities/relationships | Indefinite (until explicitly deleted) | Subject to org-level deletion requests |
| Vector embeddings | Indefinite (until source data or organization is deleted) | Entity namespaces are removed with graph cleanup; explicit vector cleanup is also supported |
| Learning outcomes | Indefinite (until explicitly deleted) | Raw task content is not stored; outcome signals are removed by organization deletion |
| Workflow definitions/runs | Indefinite (until explicitly deleted) | Queued workflow payloads are removed with workflow cleanup |

## Deletion requests

Organizations can request deletion of stored snapshots, graph data, vectors, learning outcomes, workflows, and queued workflow payloads tied to their account through `DELETE /admin/data`; see [security/data-privacy.md](../security/data-privacy.md) for process and legal/compliance caveats. Operators can run `agentweb gc` directly or pass `--schedule` to enqueue one bounded `retention_gc` job for the supervised worker. Scheduled cleanup may target one organization with `--org`, or all local organizations when no target is supplied; the optional PostgreSQL coordinator owns the job lease in distributed mode.

## Backups

Backups follow the retention window of the underlying data type and are covered under [disaster-recovery.md](disaster-recovery.md). Encrypted browser credentials and session states are not part of automatic retention GC; revoke or delete them explicitly through their administrator lifecycle endpoints.
