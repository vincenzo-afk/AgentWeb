from __future__ import annotations

import json
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "evals" / "golden_tasks.json"
tasks = json.loads(path.read_text(encoding="utf-8"))
required_categories = {
    "factual", "official-source", "technical-documentation", "framework-comparison",
    "current-information", "ambiguous", "multi-hop", "contradictory-sources",
    "negative-or-impossible", "prompt-injection", "ssrf", "malformed-input",
}
assert isinstance(tasks, list) and len(tasks) >= 24, "golden suite must contain at least 24 tasks"
ids = [item.get("id") for item in tasks]
assert all(isinstance(item, dict) and item.get("id") and "category" in item and "task" in item for item in tasks), "each golden task needs id, category, and task"
assert len(ids) == len(set(ids)), "golden task ids must be unique"
actual_categories = {item["category"] for item in tasks}
missing = required_categories - actual_categories
assert not missing, f"missing golden categories: {sorted(missing)}"
print(json.dumps({"tasks": len(tasks), "categories": sorted(actual_categories), "status": "valid"}, indent=2))
