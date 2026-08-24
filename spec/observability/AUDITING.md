# Auditing

## Distinct from Tracing
[Tracing](TRACING.md) records what a *run* did (search/browse/extract/synthesize). Auditing records security/administration-relevant *account-level* actions: key creation/revocation, scope changes, configuration changes affecting cost or safety behavior, data-deletion requests.

## Audit log schema
```
AuditEvent { id, org_id, actor, action, target, timestamp, metadata }
```

Examples: `api_key.created`, `api_key.revoked`, `monitor.frequency_cap_changed`, `data.deletion_requested`, `ranker_override.updated`.

## Retention
Audit logs are retained longer than standard operational logs, aligned with compliance-relevant retention needs (see [../security/COMPLIANCE.md](../security/COMPLIANCE.md)) — typically the same window as [usage/billing records](../../docs/operations/data-retention.md). The local-first default is 730 days; operators can set an explicit window with `agentweb gc --audit-days N`, optionally limited to one organization with `--org`. Cleanup reports the exact number of deleted events and does not mutate newer records.

## Access
Audit logs are readable by organization admins via `/admin` endpoints ([../api/AUTHORIZATION.md](../api/AUTHORIZATION.md) `admin:*` scope) but are not themselves mutable by any API caller. `GET /admin/audit` supports exact `action`, `actor`, and `target` filters plus inclusive `since`/`until` UTC time bounds before opaque-cursor pagination; cross-organization rows are never returned.
