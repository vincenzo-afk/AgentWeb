# Authorization

## Model
Scope-based access control per API key. Scopes gate access to endpoint categories, not individual records.

## Scopes

| Scope | Grants |
|---|---|
| `search:read` | `/search`, `/crawl` |
| `browser:execute` | `/browser/sessions` |
| `solve:execute` | `/solve` |
| `observe:manage` | `/observe` create/read/delete |
| `memory:read` | `/memory/*` |
| `graph:read` | `/graph/query` |
| `admin:*` | `/admin/*` |

## Enforcement
Every request's key scopes are checked against the required scope for the called endpoint before any orchestration begins; a missing scope returns `403 permission_error` per [ERROR_CODES.md](ERROR_CODES.md) without partial execution.

## Least privilege guidance
See [docs/security/secrets-management.md](../../docs/security/secrets-management.md) for recommended scoping per use case (e.g., a CI key should have `search:read` only, never `admin:*`).
