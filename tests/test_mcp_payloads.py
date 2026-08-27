import inspect
import json
import unittest

from agentweb.mcp_server import _compact_research_response


class MCPPayloadTests(unittest.TestCase):
    def test_research_defaults_to_compact_evidence(self):
        from agentweb.mcp_server import AgentWebMCPTools
        self.assertFalse(inspect.signature(AgentWebMCPTools.research).parameters["include_all_evidence"].default)
        self.assertFalse(inspect.signature(AgentWebMCPTools.parallel_research).parameters["include_all_evidence"].default)

    def test_compactor_preserves_answer_citations_and_media_but_drops_raw_page_structures(self):
        payload = {
            "answer": "A concise grounded answer.",
            "citations": [{"claim_span": [0, 8], "source_ids": ["src-1"]}],
            "evidence_gaps": [],
            "sources": [{
                "id": "src-1",
                "url": "https://example.com/docs",
                "title": "Official docs",
                "snippet": "Useful evidence",
                "structured_data": {
                    "entities": ["x"] * 1000,
                    "tables": [["large"]] * 1000,
                    "evidence_segments": {"architecture": "A" * 3000},
                    "media": {"title": "Video", "transcript": "T" * 3000},
                },
            }],
            "structured_output": {
                "frameworks": [{"framework": "Example", "facets": {"architecture": {"status": "verified", "evidence": "E" * 3000, "source_ids": ["src-1"]}}, "source_ids": ["src-1"]}],
                "references": [{"id": "src-1", "url": "https://example.com/docs", "title": "Official docs"}],
            },
        }
        compact = _compact_research_response(payload)
        encoded = json.dumps(compact)
        self.assertIn("A concise grounded answer.", encoded)
        self.assertIn("src-1", encoded)
        self.assertNotIn('"entities"', encoded)
        self.assertNotIn('"tables"', encoded)
        self.assertLess(len(encoded), 15_000)

    def test_parallel_budget_is_bounded_even_when_all_evidence_is_requested(self):
        huge = {"answer": "A" * 50_000, "sources": [{"id": "s", "url": "https://example.com", "snippet": "B" * 10_000, "structured_data": {"entities": ["C"] * 10_000}}]}
        compact = _compact_research_response(huge, include_all_evidence=True, max_answer_chars=9_000, max_sources=6)
        self.assertLess(len(json.dumps(compact)), 12_000)
        self.assertEqual(len(compact["answer"]), 9_000)


if __name__ == "__main__":
    unittest.main()
