"""Safe, additive relational migration utilities for AgentWeb."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .rdbms import POSTGRES_SCHEMA, PostgresRelationalStore


RELATIONAL_TABLES = {
    "organizations": ["id", "name", "created_at"],
    "api_keys": ["id", "org_id", "scope", "prefix", "hashed_secret", "created_at", "revoked_at"],
    "monitors": [
        "id", "org_id", "task", "status", "frequency", "target_url", "webhook_url", "created_at",
        "last_checked_at", "last_change_at", "last_event", "last_error", "last_delivery_id", "last_delivery_status",
        "last_delivery_attempts", "last_delivery_error",
    ],
    "scheduler_jobs": [
        "id", "org_id", "job_type", "monitor_id", "priority", "status", "run_at", "lease_until", "lease_token",
        "attempts", "max_attempts", "last_error", "created_at", "updated_at",
    ],
    "audit_events": ["id", "org_id", "actor", "action", "target", "timestamp", "metadata"],
    "runs": ["id", "org_id", "task", "mode", "status", "created_at", "completed_at"],
    "usage_records": ["id", "org_id", "period", "mode", "count", "cost"],
    "webhook_deliveries": ["job_id", "org_id", "monitor_id", "url", "payload_json", "status", "attempts", "max_attempts", "last_status_code", "last_error", "created_at", "updated_at", "delivered_at"],
    "webhook_delivery_attempts": ["id", "job_id", "org_id", "attempt", "delivered", "status_code", "error", "attempted_at"],
    "queue_rate_limits": ["org_id", "bucket", "tokens", "capacity", "refill_per_second", "updated_at"],
}

_JSONB_COLUMNS = {( "api_keys", "scope"), ("audit_events", "metadata"), ("webhook_deliveries", "payload_json")}
_REQUIRED_COLUMNS = {
    "organizations": ("id", "name"),
    "api_keys": ("id", "org_id", "scope", "prefix", "hashed_secret"),
    "monitors": ("id", "org_id", "task", "status", "frequency"),
    "scheduler_jobs": ("id", "org_id", "job_type", "status"),
    "audit_events": ("id", "org_id", "actor", "action", "target", "metadata"),
    "runs": ("id", "org_id", "task", "mode", "status"),
    "usage_records": ("id", "org_id", "period", "mode"),
    "webhook_deliveries": ("job_id", "org_id", "monitor_id", "url", "payload_json", "status"),
    "webhook_delivery_attempts": ("id", "job_id", "org_id", "attempt", "delivered"),
    "queue_rate_limits": ("org_id", "bucket", "tokens", "capacity", "refill_per_second"),
}
_TIMESTAMP_COLUMNS = {
    "created_at", "completed_at", "last_checked_at", "last_change_at", "run_at", "lease_until",
    "updated_at", "timestamp", "delivered_at", "attempted_at",
}


@dataclass(frozen=True)
class TableManifest:
    table: str
    row_count: int
    sha256: str
    file: str


def _canonical_row(row: dict[str, Any]) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":"), default=str)


def export_sqlite_relational(source_path: str | Path, output_dir: str | Path, dry_run: bool = False) -> dict[str, Any]:
    """Export only relational tables; the source SQLite database is never mutated."""
    source_path = Path(source_path)
    output_dir = Path(output_dir)
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
    manifests: list[dict[str, Any]] = []
    with sqlite3.connect(source_path) as connection:
        connection.row_factory = sqlite3.Row
        available = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, columns in RELATIONAL_TABLES.items():
            if table not in available:
                manifests.append({"table": table, "row_count": 0, "sha256": hashlib.sha256(b"").hexdigest(), "file": f"{table}.jsonl"})
                continue
            available_columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            selected = [column for column in columns if column in available_columns]
            if not selected:
                rows = []
            else:
                query = "SELECT " + ", ".join(selected) + f" FROM {table} ORDER BY rowid"
                rows = [{column: dict(row).get(column) for column in columns} for row in connection.execute(query)]
            digest = hashlib.sha256()
            if not dry_run:
                with (output_dir / f"{table}.jsonl").open("w", encoding="utf-8") as stream:
                    for row in rows:
                        line = _canonical_row(row)
                        stream.write(line + "\n")
                        digest.update((line + "\n").encode("utf-8"))
            else:
                for row in rows:
                    digest.update((_canonical_row(row) + "\n").encode("utf-8"))
            manifests.append({"table": table, "row_count": len(rows), "sha256": digest.hexdigest(), "file": f"{table}.jsonl"})
    manifest = {
        "format": "agentweb-relational-export-v1",
        "created_at": time.time(),
        "source": str(source_path),
        "tables": manifests,
        "destructive": False,
    }
    if not dry_run:
        (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _migration_version(manifest: dict[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_row(manifest.get("tables", [])).encode("utf-8")).hexdigest()[:32]
    return f"relational-v1:{digest}"


def _validate_manifest(export_dir: Path) -> dict[str, Any]:
    manifest_path = export_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError("migration manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "agentweb-relational-export-v1":
        raise ValueError("unsupported migration manifest format")
    for item in manifest.get("tables", []):
        path = export_dir / str(item["file"])
        if not path.is_file():
            raise ValueError(f"migration table file is missing: {item['table']}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"migration checksum mismatch: {item['table']}")
    return manifest


def _timestamp_value(value: Any, *, required: bool = False) -> Any:
    if value in (None, ""):
        if required:
            return datetime.now(timezone.utc)
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    return value


def _postgres_value(table: str, column: str, value: Any) -> Any:
    if column in _TIMESTAMP_COLUMNS:
        return _timestamp_value(value, required=column in {"created_at", "run_at", "updated_at", "timestamp"})
    if (table, column) in _JSONB_COLUMNS:
        if value in (None, ""):
            raise ValueError(f"migration row has no value for {table}.{column}")
        try:
            parsed = json.loads(value) if isinstance(value, str) else value
        except json.JSONDecodeError as error:
            raise ValueError(f"migration row has invalid JSON for {table}.{column}") from error
        try:
            from psycopg.types.json import Json  # type: ignore
        except ImportError as error:
            raise ValueError("psycopg JSON adaptation is unavailable") from error
        return Json(parsed)
    return value


def _prepare_row(table: str, row: dict[str, Any]) -> tuple[Any, ...]:
    missing = [column for column in _REQUIRED_COLUMNS.get(table, ()) if row.get(column) in (None, "")]
    if missing:
        raise ValueError(f"migration row missing required columns for {table}: {', '.join(missing)}")
    columns = RELATIONAL_TABLES[table]
    return tuple(_postgres_value(table, column, row.get(column)) for column in columns)


def import_postgres_relational(export_dir: str | Path, store: PostgresRelationalStore, dry_run: bool = False) -> dict[str, Any]:
    """Import a validated export in one transaction; the operation is additive and idempotent."""
    export_dir = Path(export_dir)
    manifest = _validate_manifest(export_dir)
    if dry_run:
        return {"status": "dry_run", "tables": manifest["tables"]}
    store.bootstrap()
    version = _migration_version(manifest)
    with store.connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version FROM schema_migrations WHERE version=%s", (version,))
            if cursor.fetchone():
                return {"status": "already_applied", "version": version}
            for item in manifest["tables"]:
                table = item["table"]
                columns = RELATIONAL_TABLES.get(table)
                if not columns:
                    raise ValueError(f"unsupported migration table: {table}")
                path = export_dir / item["file"]
                with path.open("r", encoding="utf-8") as stream:
                    for line in stream:
                        row = json.loads(line)
                        placeholders = ", ".join("%s" for _ in columns)
                        column_sql = ", ".join(columns)
                        cursor.execute(
                            f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders}) ON CONFLICT DO NOTHING",
                            _prepare_row(table, row),
                        )
            # Explicitly imported BIGSERIAL values do not advance PostgreSQL's
            # sequence automatically; reset it before future attempt inserts.
            cursor.execute(
                "SELECT setval(pg_get_serial_sequence('webhook_delivery_attempts', 'id'), "
                "COALESCE(MAX(id), 1), COUNT(*) > 0) FROM webhook_delivery_attempts"
            )
            cursor.execute("INSERT INTO schema_migrations(version) VALUES (%s)", (version,))
    return {"status": "applied", "version": version, "tables": manifest["tables"]}
