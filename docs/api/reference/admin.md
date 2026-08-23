# Admin

Organization, key, and usage management endpoints. Requires an admin-scoped API key.

## `GET /admin/keys`

Lists API keys for the authenticated organization, including scope, prefix, creation date, and revocation state. It never returns full secret values.

## `POST /admin/keys`

Creates a new organization API key with scope restrictions such as `search:read` or `extract:read`. The plaintext `sk-live-...` secret is returned only in the creation response; SQLite stores a PBKDF2-derived hash and prefix instead.

## `DELETE /admin/keys/{id}`

Revokes a key only when it belongs to the authenticated organization. Revocation also clears the short-lived authorization cache.

## `GET /admin/audit`

Returns immutable organization-scoped security events such as `api_key.created` and `api_key.revoked`. Secrets are never included in event metadata.

## `GET /admin/usage`

Returns usage and billing data:

```json
{
  "period": "2026-07",
  "requests_by_mode": { "flash": 1200, "focus": 340, "dive": 58, "monitor_checks": 5400 },
  "estimated_cost": 184.20
}
```

See [operations/cost-controls.md](../../operations/cost-controls.md) for managing spend, and [security/secrets-management.md](../../security/secrets-management.md) for key handling guidance.
