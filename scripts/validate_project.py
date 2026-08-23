"""Validate repository invariants without third-party tooling."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    openapi = (ROOT / "openapi" / "openapi.yaml").read_text(encoding="utf-8")
    required_paths = ["/solve", "/observe", "/observe/{id}", "/search", "/extract"]
    missing_paths = [path for path in required_paths if path not in openapi]
    if missing_paths:
        raise SystemExit(f"OpenAPI paths missing: {', '.join(missing_paths)}")
    if 'name = "agentweb"' not in pyproject or 'requires-python = ">=3.11"' not in pyproject:
        raise SystemExit("pyproject metadata is incomplete")
    for path in ["README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", ".github/workflows/ci.yml"]:
        if not (ROOT / path).exists():
            raise SystemExit(f"required repository file missing: {path}")
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    if not re.search(r"python-version:\s*[\"']?3\.11", workflow):
        raise SystemExit("CI must verify Python 3.11")
    print("AgentWeb repository validation passed.")


if __name__ == "__main__":
    main()
