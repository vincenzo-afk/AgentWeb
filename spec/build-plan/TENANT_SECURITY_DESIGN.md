# Tenant Isolation and Security Design

This build slice introduces organization-scoped identity and storage while preserving the local development mode and existing public contracts.

## Identity model

Every authenticated request resolves to a `Principal` containing a stable `org_id`, a redacted `key_id`, and scope claims. Environment-configured keys remain supported for local development; their organization is explicitly configured through `AGENTWEB_API_KEY_ORG` or per-key metadata. Persistent customer keys are stored in SQLite as SHA-256 hashes with a non-secret prefix, organization ID, scopes, creation time, and optional revocation time. Plaintext secrets are returned only once at creation and never persisted, traced, or logged.

When no authentication configuration exists, development requests use the explicit `development` organization. This preserves the existing local MVP behavior but does not allow an authenticated organization to read development data, and it never disables the scope check for configured keys.

## Storage isolation

Organizations are represented in SQLite. Snapshots, monitors, scheduler jobs, execution traces, and audit events carry `org_id`; all reads, updates, deletes, job claims, and trace lookups require that organization ID. Existing databases are migrated into a `legacy` organization so historical data is not silently exposed to a newly authenticated tenant. Resource IDs remain opaque, but ownership is always checked before returning a record; cross-tenant access behaves as not found.

Scheduler claims are organization-aware within the transaction. A worker can process jobs for all tenants, but it loads the owning monitor by the job's `org_id` and passes the same organization context into the checker. Browser sessions do not share cookies, storage, cache, or credentials across requests; their execution trace is tagged with the owning organization.

## Key management and audit

The first security slice adds minimal admin key lifecycle endpoints: list redacted keys, create a scoped key, revoke a key, and read immutable audit events. All require `admin:*`; all key creation and revocation actions write an audit event with the organization and actor key ID, never the secret. Admin operations are not exposed through an unauthenticated development shortcut.

## Request controls

The API authenticates before body parsing or orchestration, derives rate-limit identity from the stable organization/key identity, and applies a separate scheduled bucket to worker checks in the scheduler boundary. CORS is restricted by `AGENTWEB_ALLOWED_ORIGINS` when configured; wildcard CORS remains only for explicit local development with no configured key store. Error responses do not reveal whether another organization owns an ID.

## Explicit boundaries

This slice does not implement a distributed RDBMS, external secrets manager, graph sharing, full billing/usage accounting, or encrypted customer browser credentials. It establishes application-level tenant scoping and safe local key storage so those later components have a correct ownership boundary.
