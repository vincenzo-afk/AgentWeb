import unittest
from unittest.mock import patch

from agentweb.adaptive import ResearchPolicy, evidence_state, follow_up_queries, should_continue
from agentweb.model_router import ModelRouter
from agentweb.models import Source


class AdaptivePolicyTests(unittest.TestCase):
    def test_evidence_state_identifies_required_families(self):
        sources = [Source(id="1", url="https://en.wikipedia.org/wiki/France", title="France", snippet="Paris is the capital of France", trust_score=0.9)]
        state = evidence_state("What is the capital of France?", sources)
        self.assertIn("knowledge", state["source_families"])
        self.assertEqual(state["missing_families"], [])
        self.assertGreater(state["score"], 0)

    def test_follow_up_queries_target_missing_source_families(self):
        state = {"missing_families": ["academic", "technical"], "source_count": 1, "score": 0.2}
        queries = follow_up_queries("compare vector databases", state, 2)
        self.assertTrue(any("peer reviewed" in query for query in queries))
        self.assertTrue(any("official documentation" in query for query in queries))

    def test_evidence_gate_stops_when_target_and_score_are_met(self):
        policy = ResearchPolicy.for_mode("focus")
        state = {"source_count": 8, "missing_families": [], "score": 0.9}
        keep_going, reason = should_continue(policy, state, round_number=1, elapsed_seconds=1, tried_queries=1)
        self.assertFalse(keep_going)
        self.assertEqual(reason, "evidence_gate_satisfied")

    def test_model_router_is_disabled_without_explicit_configuration(self):
        with patch.dict("os.environ", {}, clear=False):
            for key in ("AGENTWEB_REASONING_ENDPOINT", "AGENTWEB_REASONING_API_KEY", "AGENTWEB_REASONING_MODEL"):
                __import__("os").environ.pop(key, None)
            router = ModelRouter()
            queries, decision = router.suggest_queries("test", [], [], 2)
        self.assertEqual(queries, [])
        self.assertFalse(decision.enabled)
        self.assertFalse(router.status()["enabled"])


if __name__ == "__main__":
    unittest.main()
