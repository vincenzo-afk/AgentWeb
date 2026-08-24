from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentweb.api import create_server
from agentweb.learning import LearningStore


class LearningStoreTests(unittest.TestCase):
    def test_outcomes_aggregate_without_task_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LearningStore(Path(directory) / "learning.sqlite3")
            store.record_outcome("comparison", "focus", True, 0.8, "org_a", "exec_1", 120)
            store.record_outcome("comparison", "focus", False, 0.2, "org_a", "exec_2", 220)
            store.record_outcome("comparison", "focus", True, 1.0, "org_b", "exec_3", 100)
            summary = store.summary("org_a")
            self.assertEqual(summary[0]["observations"], 2)
            self.assertEqual(summary[0]["success_rate"], 0.5)
            self.assertEqual(summary[0]["average_evidence_score"], 0.5)
            self.assertEqual(summary[0]["average_latency_ms"], 170.0)
            self.assertEqual(store.summary("org_b")[0]["observations"], 1)

    def test_validation_rejects_invalid_outcome_signals(self) -> None:
        store = LearningStore(":memory:")
        with self.assertRaises(ValueError):
            store.record_outcome("", "focus", True, 0.5)
        with self.assertRaises(ValueError):
            store.record_outcome("x", "focus", True, 1.5)
        with self.assertRaises(ValueError):
            store.record_outcome("x", "focus", True, 0.5, latency_ms=-1)


class LearningApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.server = create_server("127.0.0.1", 0, str(Path(self.temp_dir.name) / "api.sqlite3"))
        import threading
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()
        self.temp_dir.cleanup()

    def request(self, method: str, path: str, payload: dict | None = None):
        import json
        from urllib.request import Request, urlopen
        body = None if payload is None else json.dumps(payload).encode()
        request = Request(self.base_url + path, data=body, method=method, headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            return response.status, json.loads(response.read().decode())

    def test_feedback_and_summary_are_exposed(self) -> None:
        status, outcome = self.request("POST", "/v1/learning/outcomes", {"strategy": "comparison", "mode": "focus", "success": True, "evidence_score": 0.9, "latency_ms": 50})
        self.assertEqual(status, 201)
        self.assertTrue(outcome["success"])
        status, summary = self.request("GET", "/v1/learning/summary")
        self.assertEqual(status, 200)
        self.assertEqual(summary["strategies"][0]["strategy"], "comparison")
        self.assertEqual(summary["strategies"][0]["observations"], 1)


if __name__ == "__main__":
    unittest.main()
