# Admin

Organization, key, and usage management endpoints. Requires an admin-scoped API key.

## `GET /admin/keys`

Lists API keys for the organization, including scope and creation date (never returns full secret values after initial creation).

## `POST /admin/keys`

Creates a new API key with optional scope restrictions (e.g., `search`, `extract`, no `browser`, no `admin`).

## `DELETE /admin/keys/{id}`

Revokes a key.

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
