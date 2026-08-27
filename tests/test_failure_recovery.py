import unittest
from unittest.mock import patch

from agentweb.models import Source
from agentweb.synthesis import synthesize
from agentweb.ranking import RankedSource
from agentweb.mode_connectors import BranchSearchProvider, GeneralWebSearchBranch


class FailureRecoveryTests(unittest.TestCase):
    def test_branch_provider_records_failure_and_keeps_other_branch_results(self):
        class Primary:
            def search(self, query, limit=10, freshness=None):
                raise RuntimeError("primary unavailable")

        class HealthyBranch:
            name = "healthy"
            def search(self, query, limit=5, freshness=None):
                return [{"url": "https://example.test/one", "title": "One", "snippet": "evidence"}]

        provider = BranchSearchProvider(Primary(), {"focus": [HealthyBranch()]})
        results = provider.search_many(["example"], mode="focus", limit=3)
        self.assertEqual(results[0]["url"], "https://example.test/one")
        self.assertIn("primary", provider.last_metadata["failures"])

    def test_duplicate_urls_are_merged_and_branch_failure_is_not_fatal(self):
        class Primary:
            def search(self, query, limit=10, freshness=None):
                return [{"url": "https://example.test/one", "title": "Primary", "snippet": "short"}]

        class DuplicateBranch:
            name = "duplicate"
            def search(self, query, limit=5, freshness=None):
                return [{"url": "https://example.test/one", "title": "Branch", "snippet": "longer evidence"}]

        class BrokenBranch:
            name = "broken"
            def search(self, query, limit=5, freshness=None):
                raise TimeoutError("timed out")

        provider = BranchSearchProvider(Primary(), {"focus": [DuplicateBranch(), BrokenBranch()]})
        results = provider.search_many(["example"], mode="focus", limit=3)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["snippet"], "longer evidence")
        self.assertIn("broken", provider.last_metadata["failures"])

    def test_general_provider_falls_back_after_first_provider_rejection(self):
        class BlockedProvider:
            def search(self, query, limit=10, freshness=None):
                from agentweb.search import SearchProviderError
                raise SearchProviderError("blocked")

        class HealthyProvider:
            def search(self, query, limit=10, freshness=None):
                return [{"url": "https://example.test", "title": "Fallback", "snippet": "ok"}]

        with patch("agentweb.search.BraveSearchHTMLProvider", BlockedProvider), patch("agentweb.search.BingSearchHTMLProvider", HealthyProvider):
            results = GeneralWebSearchBranch().search("official documentation", limit=2)
        self.assertEqual(results[0]["title"], "Fallback")

    def test_contradictory_sources_are_returned_as_conflicts(self):
        sources = [
            Source(id="a", url="https://a.test", title="A", snippet="Price $10"),
            Source(id="b", url="https://b.test", title="B", snippet="Price $20"),
        ]
        ranked = [RankedSource(source, 0.9) for source in sources]
        result = synthesize(ranked, "Compare the price evidence", "text")
        self.assertTrue(result.conflicts)
        self.assertIn("Conflicting evidence", result.answer)

    def test_empty_sources_produce_explicit_insufficient_evidence(self):
        result = synthesize([], "Find evidence about an unavailable source", "text")
        self.assertTrue(result.insufficient_evidence)
        self.assertIn("No sufficiently reliable evidence", result.answer)


if __name__ == "__main__":
    unittest.main()
