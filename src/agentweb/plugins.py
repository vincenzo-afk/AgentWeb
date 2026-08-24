"""Process-local, organization-scoped extension hooks.

Plugins are application-provided Python callables, not remotely loaded code. The
registry validates their public contract, evaluates match predicates defensively,
and bounds every hook invocation so a broken extension falls back to core behavior.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, Mapping


_PLUGIN_TYPES = {"connector", "skill", "ranker"}
_HOOKS = {
    "connector": {"extraction_hints", "interaction_script", "ranking_bias"},
    "skill": {"plan_template", "input_schema"},
    "ranker": {"score_override"},
}


@dataclass(frozen=True)
class Plugin:
    """Validated plugin registration metadata and hook implementations."""

    name: str
    version: str
    org_id: str
    type: str
    match: Callable[[dict[str, Any]], bool]
    hooks: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name.strip()) > 120:
            raise ValueError("plugin name must contain between 1 and 120 characters")
        if not isinstance(self.version, str) or not self.version.strip() or len(self.version.strip()) > 60:
            raise ValueError("plugin version must contain between 1 and 60 characters")
        if not isinstance(self.org_id, str) or not self.org_id.strip() or len(self.org_id.strip()) > 120:
            raise ValueError("plugin org_id must contain between 1 and 120 characters")
        if self.type not in _PLUGIN_TYPES:
            raise ValueError("plugin type must be connector, skill, or ranker")
        if not callable(self.match):
            raise TypeError("plugin match must be callable")
        if not isinstance(self.hooks, Mapping) or not self.hooks:
            raise ValueError("plugin hooks must be a non-empty object")
        unknown = set(self.hooks) - _HOOKS[self.type]
        if unknown:
            raise ValueError(f"unsupported {self.type} hook: {sorted(unknown)[0]}")
        if any(not callable(value) and self.type != "connector" for value in self.hooks.values()):
            raise TypeError("skill and ranker plugin hooks must be callable")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Plugin":
        if not isinstance(value, Mapping):
            raise TypeError("plugin must be an object")
        required = {"name", "version", "org_id", "type", "match", "hooks"}
        missing = required - set(value)
        if missing:
            raise ValueError(f"missing plugin field: {sorted(missing)[0]}")
        return cls(
            name=value["name"],
            version=value["version"],
            org_id=value["org_id"],
            type=value["type"],
            match=value["match"],
            hooks=dict(value["hooks"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "version": self.version, "org_id": self.org_id, "type": self.type, "hooks": sorted(self.hooks)}


class PluginRegistry:
    """Thread-safe local registry with bounded, fail-closed hook execution."""

    def __init__(self, plugins: list[Plugin] | None = None, timeout_seconds: float = 0.10) -> None:
        if float(timeout_seconds) <= 0 or float(timeout_seconds) > 5:
            raise ValueError("timeout_seconds must be between 0 and 5")
        self.timeout_seconds = float(timeout_seconds)
        self._lock = RLock()
        self._plugins: dict[tuple[str, str], Plugin] = {}
        for plugin in plugins or []:
            self.register(plugin)

    def register(self, plugin: Plugin | Mapping[str, Any]) -> Plugin:
        normalized = plugin if isinstance(plugin, Plugin) else Plugin.from_dict(plugin)
        key = (normalized.org_id.strip(), normalized.name.strip())
        with self._lock:
            if key in self._plugins:
                raise ValueError(f"plugin already registered: {normalized.name}")
            self._plugins[key] = normalized
        return normalized

    def unregister(self, org_id: str, name: str) -> bool:
        with self._lock:
            return self._plugins.pop((str(org_id), str(name)), None) is not None

    def get(self, org_id: str, name: str) -> Plugin | None:
        with self._lock:
            return self._plugins.get((str(org_id), str(name)))

    def list(self, org_id: str | None = None, plugin_type: str | None = None) -> list[Plugin]:
        with self._lock:
            values = list(self._plugins.values())
        if org_id is not None:
            values = [item for item in values if item.org_id == str(org_id)]
        if plugin_type is not None:
            if plugin_type not in _PLUGIN_TYPES:
                raise ValueError("plugin type must be connector, skill, or ranker")
            values = [item for item in values if item.type == plugin_type]
        return sorted(values, key=lambda item: (item.name, item.version))

    def _invoke(self, function: Callable[..., Any], context: dict[str, Any]) -> Any:
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="agentweb-plugin")
        future = executor.submit(function, deepcopy(context))
        try:
            return future.result(timeout=self.timeout_seconds)
        except (Exception, FutureTimeout):
            return None
        finally:
            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

    def _matching(self, org_id: str, plugin_type: str, context: dict[str, Any]) -> list[Plugin]:
        matched: list[Plugin] = []
        for plugin in self.list(org_id, plugin_type):
            result = self._invoke(plugin.match, context)
            if result is True:
                matched.append(plugin)
        return matched

    def connector_overrides(self, org_id: str, url: str, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        """Return validated connector hook output; invalid hooks are ignored."""
        context = {"org_id": str(org_id), "url": url, "tool": tool, "params": deepcopy(params)}
        result: dict[str, Any] = {}
        matched = self._matching(str(org_id), "connector", context)
        for plugin in matched:
            for hook_name, hook_value in plugin.hooks.items():
                value = self._invoke(hook_value, context) if callable(hook_value) else deepcopy(hook_value)
                if hook_name == "extraction_hints" and isinstance(value, dict):
                    result[hook_name] = value
                elif hook_name == "interaction_script" and isinstance(value, list) and len(value) <= 20:
                    result[hook_name] = value
                elif hook_name == "ranking_bias" and isinstance(value, dict):
                    result[hook_name] = value
            if result:
                result["plugin"] = plugin.name
        return result

    def skill_hooks(self, org_id: str, task: str, inputs: dict[str, Any]) -> dict[str, Any]:
        context = {"org_id": str(org_id), "task": task, "inputs": deepcopy(inputs)}
        for plugin in self._matching(str(org_id), "skill", context):
            values: dict[str, Any] = {"plugin": plugin.name, "version": plugin.version}
            for hook_name, hook in plugin.hooks.items():
                value = self._invoke(hook, context)
                if hook_name == "plan_template" and isinstance(value, (list, tuple)) and len(value) <= 20:
                    values[hook_name] = deepcopy(list(value))
                elif hook_name == "input_schema" and isinstance(value, dict):
                    values[hook_name] = deepcopy(value)
            if "plan_template" in values:
                return values
        return {}

    def ranker_scores(self, org_id: str, source: Any, task_context: str, base_score: float) -> float:
        context = {"org_id": str(org_id), "source": source, "task_context": task_context, "base_score": float(base_score)}
        score = float(base_score)
        for plugin in self._matching(str(org_id), "ranker", context):
            hook = plugin.hooks.get("score_override")
            value = self._invoke(hook, context)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                score = float(value)
                context["base_score"] = score
        return score


_DEFAULT_REGISTRY = PluginRegistry()


def register_plugin(plugin: Plugin | Mapping[str, Any]) -> Plugin:
    return _DEFAULT_REGISTRY.register(plugin)


def plugin_registry() -> PluginRegistry:
    return _DEFAULT_REGISTRY


__all__ = ["Plugin", "PluginRegistry", "plugin_registry", "register_plugin"]
