from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .connectors import ConnectorRegistry
from .planner import Plan


@dataclass(frozen=True)
class ToolCall:
    tool: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Router:
    """Translate plans into deterministic calls and apply URL connector overrides."""

    def __init__(self, connectors: ConnectorRegistry | None = None) -> None:
        self.connectors = connectors or ConnectorRegistry()

    _ALIASES = {
        "search_each_item": "search",
        "extract_price_and_specs": "extract",
        "rank_sources": "rank",
        "synthesize_comparison": "synthesize",
    }
    _SUPPORTED = {"search", "crawl", "browser", "extract", "rank", "synthesize"}

    @staticmethod
    def _url_calls(tool: str, params: dict[str, Any]) -> list[ToolCall]:
        urls = params.get("urls")
        if not isinstance(urls, list) or not urls:
            return [ToolCall(tool, dict(params))]
        calls: list[ToolCall] = []
        for url in urls[:5]:
            if isinstance(url, str) and url.strip():
                item = dict(params)
                item.pop("urls", None)
                item["url"] = url.strip()
                calls.append(ToolCall(tool, item))
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
            if tool in {"extract", "browser"}:
                expanded = self._url_calls(tool, params)
                for call in expanded:
                    connector = self.connectors.match(call.params.get("url", ""))
                    if connector is not None:
                        enriched = dict(call.params)
                        enriched["connector"] = connector.name
                        if connector.extraction_hints:
                            enriched["extraction_hints"] = connector.extraction_hints
                        if connector.interaction_script and tool == "browser" and not enriched.get("actions"):
                            enriched["actions"] = connector.interaction_script
                        if connector.ranking_bias:
                            enriched["ranking_bias"] = connector.ranking_bias
                        call = ToolCall(call.tool, enriched)
                    calls.append(call)
            else:
                calls.append(ToolCall(tool, params))
        return calls


def route(plan: Plan) -> list[ToolCall]:
    return Router().route(plan)
