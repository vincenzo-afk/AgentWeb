# Auditing

## Distinct from Tracing
[Tracing](TRACING.md) records what a *run* did (search/browse/extract/synthesize). Auditing records security/administration-relevant *account-level* actions: key creation/revocation, scope changes, configuration changes affecting cost or safety behavior, data-deletion requests.

## Audit log schema
```
AuditEvent { id, org_id, actor, action, target, timestamp, metadata }
```

Examples: `api_key.created`, `api_key.revoked`, `monitor.frequency_cap_changed`, `data.deletion_requested`, `ranker_override.updated`.

## Retention
Audit logs are retained longer than standard operational logs, aligned with compliance-relevant retention needs (see [../security/COMPLIANCE.md](../security/COMPLIANCE.md)) — typically the same window as [usage/billing records](../../docs/operations/data-retention.md).

## Access
Audit logs are readable by organization admins via `/admin` endpoints ([../api/AUTHORIZATION.md](../api/AUTHORIZATION.md) `admin:*` scope) but are not themselves mutable by any API caller.
