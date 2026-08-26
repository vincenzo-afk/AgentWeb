import unittest

from agentweb.mode_connectors import BranchSearchProvider, semantic_queries
from agentweb.mcp_server import AgentWebMCPTools


class _Provider:
    def __init__(self):
        self.calls = []

    def search(self, query, limit=10, freshness=None):
        self.calls.append(query)
        return [{"url": "https://example.test/shared", "title": "Shared", "snippet": query}, {"url": "https://example.test/" + str(len(self.calls)), "title": query, "snippet": query}]


class _Branch:
    name = "test_branch"

    def search(self, query, limit=10, freshness=None):
        return [{"url": "https://example.test/branch", "title": "Branch", "snippet": query}]


class ModeConnectorTests(unittest.TestCase):
    def test_semantic_query_budgets_are_distinct_and_bounded(self):
        self.assertEqual(len(semantic_queries("AgentWeb", 2)), 2)
        self.assertEqual(len(semantic_queries("AgentWeb", 4)), 4)
        self.assertEqual(len(semantic_queries("AgentWeb", 6)), 6)
        self.assertEqual(len(set(semantic_queries("AgentWeb", 6))), 6)

    def test_branch_provider_merges_duplicates_and_records_metadata(self):
        primary = _Provider()
        provider = BranchSearchProvider(primary, {"focus": [_Branch()]})
        results = provider.search_many(semantic_queries("AgentWeb", 3), mode="focus", limit=2)
        self.assertEqual(len(primary.calls), 3)
        self.assertEqual(len([item for item in results if item["url"] == "https://example.test/shared"]), 1)
        self.assertEqual(provider.last_metadata["deduped_count"], 5)
        self.assertIn("test_branch", provider.last_metadata["branches"])

    def test_mcp_capabilities_expose_all_four_modes(self):
        class _Engine:
            pass
        payload = AgentWebMCPTools(_Engine()).capabilities()
        self.assertEqual(set(payload["modes"]), {"flash", "focus", "dive", "monitor"})
        self.assertIn("github_api", payload["always_on_branches"])
        self.assertIn("reddit_json", payload["always_on_branches"])


if __name__ == "__main__":
    unittest.main()


class _FailingEngine:
    def solve(self, *args, **kwargs):
        raise RuntimeError("provider failure")

    def browser_open(self, *args, **kwargs):
        raise RuntimeError("browser unavailable")

    class _Memory:
        def get_monitor(self, monitor_id):
            return None

    memory = _Memory()


class MCPGracefulErrorTests(unittest.TestCase):
    def test_research_browser_and_missing_monitor_return_structured_errors(self):
        tools = AgentWebMCPTools(_FailingEngine())
        self.assertEqual(tools.research("test", "flash")["status"], "failed")
        self.assertEqual(tools.browser_open("https://example.com")["status"], "failed")
        self.assertEqual(tools.check_monitor("mon_missing")["error_type"], "MonitorNotFound")
