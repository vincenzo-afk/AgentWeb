# Request Schema

Canonical request schemas per endpoint. See [schemas/](../../schemas/) for machine-readable JSON Schema versions of these (`solve-request.schema.json`, etc.) and [docs/api/requests.md](../../docs/api/requests.md) for the prose version.

## `SolveRequest`
```json
{ "task": "string (required)", "mode": "flash|focus|dive", "skill": "string", "inputs": "object", "webhook_url": "string", "idempotency_key": "string" }
```

## `ObserveRequest`
```json
{ "task": "string (required)", "webhook_url": "string", "frequency": "minutely|hourly|daily" }
```

## Validation rules
- `task` required, 1–2000 characters.
- `mode`, if present, must be a valid enum value; invalid values return `400 invalid_request` per [ERROR_CODES.md](ERROR_CODES.md).
- `skill`, if present, must reference a registered skill ([../module-specs/SKILLS_SPEC.md](../module-specs/SKILLS_SPEC.md)) or return `400`.
