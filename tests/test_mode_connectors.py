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

    def extract(self, *args, **kwargs):
        raise RuntimeError("rate limited")

    class _Memory:
        def get_monitor(self, monitor_id):
            return None

    memory = _Memory()


class MCPGracefulErrorTests(unittest.TestCase):
    def test_research_browser_and_missing_monitor_return_structured_errors(self):
        tools = AgentWebMCPTools(_FailingEngine())
        self.assertEqual(tools.research("test", "flash")["status"], "failed")
        self.assertEqual(tools.browser_open("https://example.com")["status"], "failed")
        self.assertEqual(tools.extract_page("https://example.com")["status"], "failed")
        self.assertEqual(tools.check_monitor("mon_missing")["error_type"], "MonitorNotFound")

    def test_capabilities_advertise_parallel_and_media_support(self):
        payload = AgentWebMCPTools(_ParallelEngine()).capabilities()
        self.assertEqual(payload["parallel_research"]["max_concurrency"], 8)
        self.assertIn("youtube", payload["media_support"])


class _ParallelEngine:
    def solve(self, task, **kwargs):
        class Response:
            def __init__(self, task):
                self.task = task

            def to_dict(self):
                return {"task": self.task, "sources": [], "mode": "focus"}

        return Response(task)


class MediaAndParallelTests(unittest.TestCase):
    def test_youtube_metadata_and_captions_are_parsed(self):
        raw = b'''<html><head><meta property="og:title" content="Demo video"></head><body><script>var ytInitialPlayerResponse = {"videoDetails":{"videoId":"abc123","title":"Demo video","author":"Demo channel"},"captions":{"playerCaptionsTracklistRenderer":{"captionTracks":[{"baseUrl":"https://video.example/captions","languageCode":"en"}]}}};</script></body></html>'''
        from agentweb.parser import parse
        parsed = parse(raw, "text/html")
        self.assertEqual(parsed.media["videoId"], "abc123")
        self.assertEqual(parsed.media["caption_tracks"][0]["language_code"], "en")

    def test_parallel_research_returns_one_result_per_task(self):
        tools = AgentWebMCPTools(_ParallelEngine())
        result = tools.parallel_research(["one", "two", "three"], "focus", 3)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["task_count"], 3)
        self.assertEqual([item["task"] for item in result["results"]], ["one", "two", "three"])


class _AdaptiveEngine:
    class _Response:
        def to_dict(self):
            return {"answer": "adaptive", "research_trace": {"stop_reason": "evidence_gate_satisfied"}}

    def __init__(self):
        self.calls = []

    def solve(self, task, **kwargs):
        self.calls.append((task, kwargs))
        return self._Response()


class AdaptiveMCPContractTests(unittest.TestCase):
    def test_research_forwards_adaptive_controls(self):
        engine = _AdaptiveEngine()
        result = AgentWebMCPTools(engine).research("compare two sources", "dive", 4, 7, 8, True)
        self.assertEqual(result["research_trace"]["stop_reason"], "evidence_gate_satisfied")
        self.assertEqual(engine.calls[0][1]["max_rounds"], 4)
        self.assertEqual(engine.calls[0][1]["max_concurrency"], 7)
        self.assertEqual(engine.calls[0][1]["evidence_target"], 8)
