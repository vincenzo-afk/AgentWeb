import unittest

from agentweb.engine import AgentWebEngine
from agentweb.models import Source
from agentweb.quality import factual_gate, official_target_hosts
from agentweb.ranking import rank


class QualityPolicyTests(unittest.TestCase):
    def test_exact_official_intents_have_target_domains(self):
        self.assertIn("modelcontextprotocol.io", official_target_hosts("Find the official MCP specification homepage"))
        self.assertIn("developers.openai.com", official_target_hosts("OpenAI Agents SDK documentation"))
        self.assertIn("docs.python.org", official_target_hosts("official Python asyncio documentation"))

    def test_target_domain_outranks_unrelated_relevant_page(self):
        sources = [
            Source(id="wiki", url="https://en.wikipedia.org/wiki/Model_Context_Protocol", title="Model Context Protocol", snippet="A general encyclopedia entry about MCP."),
            Source(id="official", url="https://modelcontextprotocol.io/docs/getting-started/intro", title="Model Context Protocol documentation", snippet="Official MCP specification and documentation."),
        ]
        ranked = rank(sources, "Find the official Model Context Protocol specification homepage")
        self.assertEqual(ranked[0].source.id, "official")

    def test_boiling_point_requires_explicit_value(self):
        unsupported = Source(id="topic", url="https://en.wikipedia.org/wiki/Boiling_point", title="Boiling point", snippet="A discussion of boiling water and reactors.")
        self.assertFalse(factual_gate("What is the boiling point of water at sea level?", [unsupported]).supported)
        supported = Source(id="fact", url="https://example.test", title="Water properties", snippet="At sea level, water boils at 100 degrees C (212 degrees F).")
        self.assertTrue(factual_gate("What is the boiling point of water at sea level?", [supported]).supported)

    def test_engine_abstains_when_factual_value_is_not_supported(self):
        class TopicOnlyProvider:
            def search_many(self, queries, mode, limit=10, freshness=None):
                return [{"url": "https://fixture.invalid/boiling-point", "title": "Boiling point", "snippet": "A discussion of boiling water and reactors."}]

        engine = AgentWebEngine()
        engine.search_provider = TopicOnlyProvider()
        response = engine.solve("What is the boiling point of water at sea level?", mode="focus", max_rounds=1)
        self.assertTrue(response.insufficient_evidence)
        self.assertIn("factual_claim_support", response.evidence_gaps)
        self.assertNotIn("100", response.answer)


if __name__ == "__main__":
    unittest.main()
