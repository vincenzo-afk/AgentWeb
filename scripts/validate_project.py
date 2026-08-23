"""Validate repository invariants without third-party tooling."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    openapi = (ROOT / "openapi" / "openapi.yaml").read_text(encoding="utf-8")
    required_paths = ["/health", "/solve", "/observe", "/observe/{id}", "/search", "/crawl", "/browser/sessions", "/extract", "/memory/{target}", "/report/{execution_id}", "/admin/keys", "/admin/keys/{id}", "/admin/audit"]
    missing_paths = [path for path in required_paths if path not in openapi]
    if missing_paths:
        raise SystemExit(f"OpenAPI paths missing: {', '.join(missing_paths)}")
    if 'name = "agentweb"' not in pyproject or 'requires-python = ">=3.11"' not in pyproject:
        raise SystemExit("pyproject metadata is incomplete")
    for path in [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".github/workflows/ci.yml",
        "src/agentweb/secrets.py",
        "src/agentweb/rdbms.py",
        "src/agentweb/migrations.py",
        "spec/build-plan/SECRETS_RDBMS_DESIGN.md",
        "docs/operations/rdbms-migration.md",
    ]:
        if not (ROOT / path).exists():
            raise SystemExit(f"required repository file missing: {path}")
    for schema_path in (ROOT / "schemas").glob("*.json"):
        json.loads(schema_path.read_text(encoding="utf-8"))
    monitor_schema = json.loads((ROOT / "schemas" / "monitor.schema.json").read_text(encoding="utf-8"))
    if "org_id" not in monitor_schema.get("properties", {}):
        raise SystemExit("monitor schema is missing org_id")
    response_schema = json.loads((ROOT / "schemas" / "solve-response.schema.json").read_text(encoding="utf-8"))
    if "insufficient_evidence" not in response_schema.get("properties", {}):
        raise SystemExit("solve response schema is missing insufficient_evidence")
    if 'postgres = ["psycopg[binary]>=3.1"]' not in pyproject:
        raise SystemExit("PostgreSQL optional dependency is missing")
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    if not re.search(r"python-version:\s*[\"']?3\.11", workflow):
        raise SystemExit("CI must verify Python 3.11")
    print("AgentWeb repository validation passed.")


if __name__ == "__main__":
    main()
