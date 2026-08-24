from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .planner import Plan


@dataclass(frozen=True)
class ToolCall:
    tool: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Router:
    """Translate a validated plan into deterministic local execution calls."""

    _ALIASES = {
        "search_each_item": "search",
        "extract_price_and_specs": "extract",
        "rank_sources": "rank",
        "synthesize_comparison": "synthesize",
    }
    _SUPPORTED = {"search", "crawl", "browser", "extract", "rank", "synthesize"}

    @staticmethod
    def _extract_calls(params: dict[str, Any]) -> list[ToolCall]:
        urls = params.get("urls")
        if not isinstance(urls, list) or not urls:
            return [ToolCall("extract", dict(params))]
        calls: list[ToolCall] = []
        for url in urls[:5]:
            if isinstance(url, str) and url.strip():
                item = dict(params)
                item.pop("urls", None)
                item["url"] = url.strip()
                calls.append(ToolCall("extract", item))
        return calls

    def route(self, plan: Plan) -> list[ToolCall]:
        if not isinstance(plan, Plan):
            raise TypeError("plan must be a Plan")
        calls: list[ToolCall] = []
        for step in plan.steps:
            if step.type not in self._ALIASES and step.type not in self._SUPPORTED:
                raise ValueError(f"unsupported plan step: {step.type}")
            tool = self._ALIASES.get(step.type, step.type)
            params = dict(step.params)
            if tool == "extract":
                calls.extend(self._extract_calls(params))
            else:
                calls.append(ToolCall(tool, params))
        return calls


def route(plan: Plan) -> list[ToolCall]:
    return Router().route(plan)
