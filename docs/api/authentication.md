# Authentication

AgentWeb uses bearer API keys.

```
Authorization: Bearer sk-live-...
```

## Key types

- **Live keys** (`sk-live-...`) — production access, billed usage.
- **Test keys** (`sk-test-...`) — sandboxed, non-billed, rate-limited more aggressively, useful for development.

## Scoping

Keys can be scoped to specific capabilities (e.g., read-only `search`/`extract` access without `browser` or `admin` access) at the organization level. Persistent keys are stored as PBKDF2-derived hashes and are never returned after creation. Every request resolves to one organization and endpoint scopes are checked before orchestration. See [reference/admin.md](reference/admin.md).

## Rotation

Rotate keys periodically and immediately after any suspected exposure. Multiple active keys per organization are supported so rotation doesn't require downtime. Revocation invalidates the durable key and clears the short-lived scope cache.

## Handling recommendations

Never embed keys in client-side code. See [security/secrets-management.md](../security/secrets-management.md) for production handling guidance.
