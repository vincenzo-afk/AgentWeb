# Versioning

The API is versioned via the URL path:

```
https://api.agentweb.dev/v1/...
```

The runtime accepts the documented `/v1/...` path prefix for every public API route. Bare paths such as `/solve` and `/observe` remain available as a local-compatibility bridge, but successful bare-path responses include `Deprecation: true`; new clients should use `/v1`. Unsupported future major prefixes such as `/v2/...` are not routed to v1 handlers.

## Policy

- Breaking changes are only introduced in a new major version (`v2`, etc.).
- Additive changes (new optional fields, new endpoints) may appear within `v1` without a version bump.
- Deprecations are announced with a minimum notice period and a `Deprecation` response header before removal. The current bare-path compatibility bridge is marked with `Deprecation: true` and is not the canonical public form.

## SDK versioning

SDKs follow semantic versioning and track the API version they were built against. See [sdk/index.md](../sdk/index.md).

See [CHANGELOG.md](../../CHANGELOG.md) for release history.
