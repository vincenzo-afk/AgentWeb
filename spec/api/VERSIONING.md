# Versioning

See [docs/api/versioning.md](../../docs/api/versioning.md) for the usage-facing policy. Build-level rule: any change that alters the meaning of an existing field, removes a field, or changes required-ness requires a new major version path (`/v2`); additive fields and new optional parameters may ship within `v1`. Deprecated fields carry a `Deprecation` response header for a minimum notice period before removal.
