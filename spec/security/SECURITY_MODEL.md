# Security Model

## Zones and isolation
See [../architecture/NETWORK_ARCHITECTURE.md](../architecture/NETWORK_ARCHITECTURE.md) — only execution workers (Search/Crawl/Browser/Extract) have outbound internet access; all other components are confined to the internal service mesh.

## Browser sandboxing
Per-request isolated sessions, resource-limited, restricted egress. See [../../docs/security/sandboxing.md](../../docs/security/sandboxing.md) and [../module-specs/BROWSER_SPEC.md](../module-specs/BROWSER_SPEC.md).

## AuthN/AuthZ
Bearer API keys with scope-based authorization, enforced before orchestration begins. See [../api/AUTHENTICATION.md](../api/AUTHENTICATION.md) and [../api/AUTHORIZATION.md](../api/AUTHORIZATION.md).

## Data protection
Organizational isolation of snapshot/graph/trace data by default; explicit opt-in required for any cross-organization graph intelligence sharing. See [PRIVACY_MODEL.md](PRIVACY_MODEL.md).

## Full threat enumeration
See [../../docs/security/threat-model.md](../../docs/security/threat-model.md).
