# Data Retention

## Retained data types

| Data | Default retention | Notes |
|---|---|---|
| Snapshots ([Memory](../core/memory.md)) | 90 days | Longer retention available for audit/compliance use cases |
| Execution graphs/traces | 30 days | Needed for [debugging](../getting-started/debugging-basics.md) and replay |
| Idempotency keys | 24 hours | See [api/idempotency.md](../api/idempotency.md) |
| API usage/billing records | 24 months | For account history and invoicing |
| Security audit events | 730 days | Local default; configurable through `agentweb gc --audit-days`, with optional organization scoping |
| Graph entities/relationships | Indefinite (until explicitly deleted) | Subject to org-level deletion requests |

## Deletion requests

Organizations can request deletion of stored snapshots and graph data tied to their account; see [security/data-privacy.md](../security/data-privacy.md) for the process and any legal/compliance caveats.

## Backups

Backups follow the retention window of the underlying data type and are covered under [disaster-recovery.md](disaster-recovery.md).
