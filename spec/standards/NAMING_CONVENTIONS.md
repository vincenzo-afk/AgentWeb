# Naming Conventions

## API / wire format
`snake_case` for JSON field names (`execution_id`, `trust_score`), matching [../api/RESPONSE_SCHEMA.md](../api/RESPONSE_SCHEMA.md).

## SDKs
`camelCase` in JavaScript/TypeScript, `snake_case` in Python — each SDK follows its language's idiomatic convention even though the wire format is fixed (see [../../docs/sdk/types.md](../../docs/sdk/types.md)).

## Internal modules
Module names match their spec file (minus `_SPEC` suffix): `Planner`, `Router`, `Extractor`, etc. — see [../architecture/MODULES.md](../architecture/MODULES.md).

## Endpoints
Verb-free, resource-oriented paths (`/observe`, not `/createMonitor`); sub-resources nested (`/observe/{id}`).

## Documentation files
This spec tree uses `SCREAMING_SNAKE_CASE.md` for build-spec documents (this file included); the parallel `docs/` tree uses `lowercase-hyphenated.md` for developer-facing prose docs — the two conventions intentionally distinguish "build spec" from "usage doc."
