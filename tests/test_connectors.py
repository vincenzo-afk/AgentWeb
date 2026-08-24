from __future__ import annotations

import unittest

from agentweb.connectors import Connector, ConnectorRegistry
from agentweb.models import Source
from agentweb.planner import Plan, PlanStep
from agentweb.ranking import rank
from agentweb.router import Router


class ConnectorTests(unittest.TestCase):
    def test_longest_matching_path_prefix_wins(self) -> None:
        registry = ConnectorRegistry([
            Connector("github", "github.com", extraction_hints={"title": "string"}),
            Connector("github-releases", "https://github.com/org/repo/releases", extraction_hints={"published": "date"}),
        ])
        self.assertEqual(registry.match("https://github.com/org/repo/releases/latest").name, "github-releases")
        self.assertEqual(registry.match("https://github.com/org/repo/issues").name, "github")
        self.assertIsNone(registry.match("https://example.com/page"))

    def test_router_applies_connector_hints_and_default_actions(self) -> None:
        connector = Connector(
            "docs",
            "docs.example.com",
            extraction_hints={"title": "string"},
            interaction_script=[{"type": "wait_for", "selector": "main"}],
            ranking_bias={"boost": ["release"]},
        )
        router = Router(ConnectorRegistry([connector]))
        plan = Plan("plan_1", (PlanStep("browser", {"url": "https://docs.example.com/release"}),), "focus", "lookup")
        call = router.route(plan)[0]
        self.assertEqual(call.params["connector"], "docs")
        self.assertEqual(call.params["extraction_hints"], {"title": "string"})
        self.assertEqual(call.params["actions"], connector.interaction_script)
        self.assertEqual(call.params["ranking_bias"], {"boost": ["release"]})

    def test_ranking_bias_changes_only_matching_source(self) -> None:
        sources = [
            Source("a", "https://example.com/a", title="release notes", snippet="release"),
            Source("b", "https://example.com/b", title="other", snippet="other"),
        ]
        baseline = rank(sources, "release")
        biased = rank(sources, "release", {"b": {"penalize": ["other"]}})
        self.assertEqual(baseline[0].source.id, "a")
        self.assertLess(next(item.score for item in biased if item.source.id == "b"), next(item.score for item in baseline if item.source.id == "b"))


if __name__ == "__main__":
    unittest.main()
