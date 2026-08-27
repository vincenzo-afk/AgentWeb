import unittest

from agentweb.framework_comparison import build_comparison, comparison_queries, is_framework_comparison
from agentweb.models import Source
from agentweb.ranking import RankedSource


class FrameworkComparisonTests(unittest.TestCase):
    task = (
        "I’m evaluating the current state of AI agent frameworks in 2026. Compare OpenAI Agents SDK, "
        "Anthropic’s Claude Agent SDK, Google’s Agent Development Kit (ADK), LangGraph, and Microsoft AutoGen. "
        "Research the latest official documentation and recent releases as of August 2026."
    )

    def test_exact_prompt_is_detected_and_fanned_out(self):
        self.assertTrue(is_framework_comparison(self.task))
        queries = comparison_queries(self.task)
        self.assertEqual(len(queries), 5)
        self.assertTrue(any("OpenAI Agents SDK" in query for query in queries))
        self.assertTrue(any("Claude Agent SDK" in query for query in queries))
        self.assertTrue(any("Google Agent Development Kit" in query for query in queries))
        self.assertTrue(any("LangGraph" in query for query in queries))
        self.assertTrue(any("Microsoft AutoGen" in query for query in queries))

    def test_comparison_emits_matrix_references_gaps_and_claim_citations(self):
        rows = [
            Source("openai", "https://developers.openai.com/api/docs/guides/agents", "OpenAI Agents SDK", "Current version release changelog architecture agent loop function calling tools MCP memory sessions state agents as tools deployment limitations license", trust_score=0.8),
            Source("claude", "https://code.claude.com/docs/en/agent-sdk/overview", "Claude Agent SDK overview", "Current version release changelog architecture agent loop function calling tools MCP context management sessions subagents deployment limitations commercial terms license", trust_score=0.8),
            Source("google", "https://adk.dev/", "Google Agent Development Kit documentation", "Current version release changelog architecture workflow function calling tools MCP session state memory multi-agent deployment Vertex AI limitations Apache license", trust_score=0.8),
            Source("langgraph", "https://docs.langchain.com/oss/python/langgraph/overview", "LangGraph overview", "Current version release changelog graph architecture tool calling MCP persistence checkpoint memory multi-agent deployment cloud limitations MIT license", trust_score=0.8),
            Source("autogen", "https://microsoft.github.io/autogen/stable/", "Microsoft AutoGen", "Current version release changelog event-driven architecture tools MCP workbench state memory AgentChat multi-agent deployment limitations MIT license", trust_score=0.8),
        ]
        answer, considered, citations, structured, score, gaps = build_comparison([RankedSource(source, 0.9) for source in rows], self.task)
        for label in ("OpenAI Agents SDK", "Anthropic Claude Agent SDK", "Google Agent Development Kit (ADK)", "LangGraph", "Microsoft AutoGen"):
            self.assertIn(label, answer)
        self.assertIn("## References", answer)
        self.assertEqual(len(structured["frameworks"]), 5)
        self.assertGreaterEqual(len(structured["references"]), 5)
        self.assertTrue(citations)
        self.assertGreater(score, 0.5)
        self.assertIsInstance(gaps, list)
        self.assertIn("evidence_gaps", structured)


if __name__ == "__main__":
    unittest.main()
