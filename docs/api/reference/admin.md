# Admin

Organization, key, and usage management endpoints. Requires an admin-scoped API key.

## `GET /admin/keys`

Lists API keys for the authenticated organization, including scope, prefix, creation date, and revocation state. It never returns full secret values.

## `POST /admin/keys`

Creates a new organization API key with scope restrictions such as `search:read` or `extract:read`. The plaintext `sk-live-...` secret is returned only in the creation response; SQLite stores a PBKDF2-derived hash and prefix instead.

## `DELETE /admin/keys/{id}`

Revokes a key only when it belongs to the authenticated organization. Revocation also clears the short-lived authorization cache.

## `GET /admin/audit`

Returns immutable organization-scoped security events such as `api_key.created` and `api_key.revoked`. Secrets are never included in event metadata. Optional exact-match filters are available for `action`, `actor`, and `target`; `since` and `until` apply inclusive Unix timestamps or ISO-8601 UTC timestamps. Filters are applied before the bounded opaque-cursor pagination, so the returned cursor must be reused with the same filter set.

For example, `GET /admin/audit?action=api_key.created&since=2026-01-01T00:00:00Z&limit=25` returns matching events only. Invalid timestamps, reversed ranges, empty filters, and filters longer than 200 characters return `400`.

## `GET /admin/usage`

Returns organization-scoped usage and local estimated billing data. If `period` is omitted, the current UTC month is used. The local MVP records one request for each completed solve and one check for each active monitor attempt; the estimate uses deterministic mode heuristics and is not an external provider invoice.

Returns usage and billing data:

```json
{
  "period": "2026-07",
  "requests_by_mode": { "flash": 1200, "focus": 340, "dive": 58, "monitor_checks": 5400 },
  "estimated_cost": 184.20
}
```

List responses from `/admin/keys` and `/admin/audit` include `data`, `next_cursor`, and `has_more`; pass the returned cursor unchanged to request the next page. Audit records are retained by the local maintenance command for 730 days by default and can be removed explicitly with `agentweb gc --audit-days N`, optionally scoped with `--org`. See [operations/cost-controls.md](../../operations/cost-controls.md) for managing spend, and [security/secrets-management.md](../../security/secrets-management.md) for key handling guidance.
