"""Optional model-assisted routing with deterministic fallback.

The default AgentWeb deployment has no model endpoint configured, so this
module is inert unless an operator explicitly supplies a compatible endpoint.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ModelDecision:
    enabled: bool
    model: str | None = None
    reason: str = "disabled"


class ModelRouter:
    def __init__(self) -> None:
        self.endpoint = os.getenv("AGENTWEB_REASONING_ENDPOINT", "").strip().rstrip("/")
        self.api_key = os.getenv("AGENTWEB_REASONING_API_KEY", "").strip()
        self.model = os.getenv("AGENTWEB_REASONING_MODEL", "").strip() or None
        self.timeout = max(2.0, min(float(os.getenv("AGENTWEB_REASONING_TIMEOUT_SECONDS", "12")), 30.0))

    @property
    def enabled(self) -> bool:
        return bool(self.endpoint and self.api_key and self.model)

    def status(self) -> dict[str, object]:
        return {"enabled": self.enabled, "model": self.model if self.enabled else None, "reason": "configured" if self.enabled else "not_configured"}

    def suggest_queries(self, task: str, existing_queries: list[str], missing_families: list[str], max_queries: int = 4) -> tuple[list[str], ModelDecision]:
        if not self.enabled:
            return [], ModelDecision(False, reason="not_configured")
        schema = {"type": "object", "properties": {"queries": {"type": "array", "items": {"type": "string"}, "maxItems": max_queries}}, "required": ["queries"], "additionalProperties": False}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return only JSON. Suggest short, non-duplicative public-web research queries that close the listed evidence gaps. Never request credentials or private data."},
                {"role": "user", "content": json.dumps({"task": task, "existing_queries": existing_queries[-12:], "missing_source_families": missing_families}, ensure_ascii=False)},
            ],
            "temperature": 0,
            "max_tokens": 600,
            "response_format": {"type": "json_schema", "json_schema": {"name": "research_queries", "strict": True, "schema": schema}},
        }
        request = Request(self.endpoint + "/chat/completions", data=json.dumps(payload).encode(), method="POST", headers={"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}", "User-Agent": "AgentWeb/0.13"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read(500_000).decode("utf-8", errors="replace"))
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "") if isinstance(result, dict) else ""
            parsed = json.loads(content) if isinstance(content, str) else {}
            queries = [str(query).strip() for query in parsed.get("queries", []) if isinstance(query, str) and query.strip()]
            return list(dict.fromkeys(queries))[:max_queries], ModelDecision(True, self.model, "configured")
        except Exception as error:
            return [], ModelDecision(True, self.model, f"fallback:{type(error).__name__}")
