# Privacy Model

## Data categories
- Customer task descriptions — organization-scoped, never shared.
- Snapshots/extracted content from third-party pages — organization-scoped by default.
- Graph entities/relations — may be shared in de-identified, aggregate form across organizations *only* with explicit opt-in (see [../../docs/security/data-privacy.md](../../docs/security/data-privacy.md)); an organization's specific task history is never exposed even when its discoveries contribute to shared graph intelligence.
- Execution traces — organization-scoped, retained per [../../docs/operations/data-retention.md](../../docs/operations/data-retention.md).

## Deletion
Organizations can request deletion of stored snapshots, traces, and their contribution to graph data; deletion propagates through backups within the standard retention/backup cycle.

## Default posture
Opt-out of cross-organization sharing is the default; opt-in is required, not assumed.
