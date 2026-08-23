# Production RDBMS Migration

This runbook covers the additive SQLite-to-PostgreSQL migration boundary implemented by AgentWeb. It does not migrate snapshots, graph data, or execution traces; those stores have separate contracts.

## Preconditions

Set `AGENTWEB_ENV=staging` or `production`. Platform secrets must come from an external provider: use `AGENTWEB_SECRET_PROVIDER=command` with an executable that accepts a validated name such as `DATABASE_URL` and writes only the value to stdout. Install the optional driver with `python -m pip install --editable '.[production]'`. The target `DATABASE_URL` must use `postgresql://` or `postgres://`.

Do not place credentials in the migration directory, command-line arguments, logs, manifests, or committed files. The export contains one-way API-key hashes because those rows must preserve authentication during cutover; protect the directory like the source database and delete it after the transfer window.

## Export and validation

The export is read-only against the SQLite source. It emits one JSON Lines file per relational table and a checksum manifest:

```bash
agentweb migrate-export --source agentweb.sqlite3 --output ./migration-export --dry-run
agentweb migrate-export --source agentweb.sqlite3 --output ./migration-export
```

The exporter projects legacy SQLite schemas into the production column set, fills fields absent from old local databases with null, and reports row counts and SHA-256 checksums. Check the manifest into the deployment evidence system only if that system is approved for sensitive migration metadata; do not commit it to this repository.

## Import and smoke test

First run a dry-run against the production-shaped secret provider:

```bash
AGENTWEB_ENV=production \
AGENTWEB_SECRET_PROVIDER=command \
AGENTWEB_SECRET_COMMAND=/secure/bin/agentweb-secrets \
agentweb migrate-import --input ./migration-export --dry-run
```

Then apply the validated manifest:

```bash
AGENTWEB_ENV=production \
AGENTWEB_SECRET_PROVIDER=command \
AGENTWEB_SECRET_COMMAND=/secure/bin/agentweb-secrets \
agentweb migrate-import --input ./migration-export
```

The importer bootstraps `schema_migrations`, organizations, API keys, runs, monitors, usage records, and the required organization indexes. It validates every file checksum before opening the target transaction. The import is additive and idempotent: a recorded `relational-v1` migration is not applied twice, and no destructive down-migration is provided.

After import, run the health endpoint and a representative authenticated request for each enabled scope. Confirm that an organization can read only its own monitors, traces, keys, and audit events. Keep the old SQLite deployment available until smoke tests pass and the rollback window closes.

## Rollback

If migration validation or smoke tests fail, stop the new API tier first. Continue on the previous SQLite-compatible release, preserve the failed manifest and database diagnostics securely, and correct the import or schema before retrying. Do not delete or alter the source SQLite database as part of rollback. Because the migration is additive, data-store rollback is not a destructive down-migration operation.
