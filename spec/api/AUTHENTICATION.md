# Authentication

See [docs/api/authentication.md](../../docs/api/authentication.md) for usage. Build-level contract: bearer API keys (`sk-live-...` / `sk-test-...`), validated on every request against the key store ([../data/DATABASE_SCHEMA.md](../data/DATABASE_SCHEMA.md)), with scope claims cached briefly to avoid a DB round-trip per request. See [AUTHORIZATION.md](AUTHORIZATION.md) for what scopes control.
