# Versioning

The API is versioned via the URL path:

```
https://api.agentweb.dev/v1/...
```

## Policy

- Breaking changes are only introduced in a new major version (`v2`, etc.).
- Additive changes (new optional fields, new endpoints) may appear within `v1` without a version bump.
- Deprecations are announced with a minimum notice period and a `Deprecation` response header before removal.

## SDK versioning

SDKs follow semantic versioning and track the API version they were built against. See [sdk/index.md](../sdk/index.md).

See [CHANGELOG.md](../../CHANGELOG.md) for release history.
