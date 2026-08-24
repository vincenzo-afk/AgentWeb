from __future__ import annotations

import time
import unittest

from agentweb.models import Source
from agentweb.planner import Planner
from agentweb.plugins import Plugin, PluginRegistry
from agentweb.ranking import rank
from agentweb.router import Router
from agentweb.planner import Plan, PlanStep


class PluginRegistryTests(unittest.TestCase):
    def test_plugins_are_organization_scoped_and_versioned(self) -> None:
        registry = PluginRegistry()
        plugin = registry.register(
            {
                "name": "rank-v1",
                "version": "1.0.0",
                "org_id": "org-a",
                "type": "ranker",
                "match": lambda context: True,
                "hooks": {"score_override": lambda context: 0.91},
            }
        )
        self.assertEqual(plugin.to_dict()["version"], "1.0.0")
        self.assertEqual([item.name for item in registry.list("org-a")], ["rank-v1"])
        self.assertEqual(registry.list("org-b"), [])
        self.assertIsNone(registry.get("org-b", "rank-v1"))

    def test_connector_plugin_enriches_matching_router_calls(self) -> None:
        registry = PluginRegistry()
        registry.register(
            Plugin(
                name="docs-connector",
                version="1.0.0",
                org_id="org-a",
                type="connector",
                match=lambda context: context["url"].startswith("https://docs.example"),
                hooks={
                    "extraction_hints": {"published": "date"},
                    "interaction_script": [{"type": "wait_for", "selector": "main"}],
                    "ranking_bias": {"boost": ["release"]},
                },
            )
        )
        plan = Plan("p1", (PlanStep("browser", {"url": "https://docs.example/release"}),), "focus", "lookup")
        call = Router(plugins=registry).route(plan, org_id="org-a")[0]
        self.assertEqual(call.params["plugin_connector"], "docs-connector")
        self.assertEqual(call.params["extraction_hints"], {"published": "date"})
        self.assertEqual(call.params["actions"], [{"type": "wait_for", "selector": "main"}])
        self.assertEqual(call.params["ranking_bias"], {"boost": ["release"]})
        other = Router(plugins=registry).route(plan, org_id="org-b")[0]
        self.assertNotIn("plugin_connector", other.params)

    def test_skill_plugin_provides_bounded_plan_template(self) -> None:
        registry = PluginRegistry()
        registry.register(
            {
                "name": "research-skill",
                "version": "2.0.0",
                "org_id": "org-a",
                "type": "skill",
                "match": lambda context: "regulatory" in context["task"].lower(),
                "hooks": {
                    "plan_template": lambda context: [
                        {"type": "search", "params": {"limit": 2}},
                        {"type": "synthesize", "params": {"output_format": "timeline"}},
                    ],
                    "input_schema": lambda context: {"type": "object"},
                },
            }
        )
        plan = Planner(plugins=registry).plan("Regulatory update", org_id="org-a")
        self.assertEqual(plan.skill, "plugin:research-skill")
        self.assertEqual([step.type for step in plan.steps], ["search", "synthesize"])
        generic = Planner(plugins=registry).plan("Regulatory update", org_id="org-b")
        self.assertIsNone(generic.skill)

    def test_ranker_override_and_broken_hook_fall_back(self) -> None:
        source = Source("a", "https://example.com/a", title="release", snippet="release")
        registry = PluginRegistry()
        registry.register(
            {
                "name": "override",
                "version": "1.0.0",
                "org_id": "org-a",
                "type": "ranker",
                "match": lambda context: context["source"].id == "a",
                "hooks": {"score_override": lambda context: 0.88},
            }
        )
        registry.register(
            {
                "name": "broken",
                "version": "1.0.0",
                "org_id": "org-a",
                "type": "ranker",
                "match": lambda context: (_ for _ in ()).throw(RuntimeError("broken match")),
                "hooks": {"score_override": lambda context: 0.01},
            }
        )
        ranked = rank([source], "release", plugins=registry, org_id="org-a")
        self.assertEqual(ranked[0].score, 0.88)
        baseline = rank([source], "release", plugins=registry, org_id="org-b")
        self.assertNotEqual(baseline[0].score, 0.88)

    def test_slow_plugin_hook_is_skipped(self) -> None:
        source = Source("a", "https://example.com/a", title="release", snippet="release")
        registry = PluginRegistry(timeout_seconds=0.01)

        def slow(context):
            time.sleep(0.05)
            return 0.01

        registry.register(
            {
                "name": "slow",
                "version": "1.0.0",
                "org_id": "org-a",
                "type": "ranker",
                "match": lambda context: True,
                "hooks": {"score_override": slow},
            }
        )
        ranked = rank([source], "release", plugins=registry, org_id="org-a")
        self.assertGreater(ranked[0].score, 0.01)


if __name__ == "__main__":
    unittest.main()
