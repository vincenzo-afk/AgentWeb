from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

from agentweb.api import AgentWebHandler
from agentweb.engine import AgentWebEngine
from agentweb.fetch import html_to_text
from agentweb.memory import MemoryStore


class FixtureHandler(BaseHTTPRequestHandler):
    body = b"<html><head><title>Fixture</title><meta name='description' content='A fixture page'></head><body><h1>Hello</h1><p>AgentWeb test content.</p></body></html>"

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_args):
        pass


class AgentWebTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        self.thread = threading.Thread(target=self.fixture.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.fixture.server_port}/fixture"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.temp_dir.name) / "test.sqlite3")
        self.engine = AgentWebEngine(self.store)

    def tearDown(self):
        self.fixture.shutdown()
        self.fixture.server_close()
        self.temp_dir.cleanup()

    def test_html_to_text_removes_scripts(self):
        self.assertEqual(html_to_text("<p>Hello</p><script>ignore()</script>"), "Hello")

    def test_snapshot_reports_only_second_content_change(self):
        self.assertFalse(self.store.save_snapshot("k", self.url, "first", "now"))
        self.assertFalse(self.store.save_snapshot("k", self.url, "first", "later"))
        self.assertTrue(self.store.save_snapshot("k", self.url, "second", "latest"))

    def test_extract_returns_title_and_text(self):
        data = self.engine.extract(self.url)
        self.assertEqual(data["title"], "Fixture")
        self.assertIn("AgentWeb test content", data["text"])
        self.assertGreater(data["trust_score"], 0)

    def test_solve_direct_url_returns_citation(self):
        response = self.engine.solve(f"Summarize {self.url}", mode="focus")
        self.assertEqual(response.mode, "focus")
        self.assertEqual(len(response.sources), 1)
        self.assertEqual(response.citations[0].source_ids, [response.sources[0].id])

    def test_monitor_lifecycle_and_snapshot_reuse(self):
        monitor = self.engine.create_monitor(f"Watch {self.url}", "hourly")
        first = self.engine.check_monitor(monitor)
        self.assertIsNone(first.last_change_at)
        FixtureHandler.body = b"<html><title>Changed</title><body>changed</body></html>"
        second = self.engine.check_monitor(first)
        self.assertIsNotNone(second.last_change_at)
        self.assertTrue(self.store.delete_monitor(monitor.id))

    def test_health_endpoint(self):
        api = __import__("agentweb.api", fromlist=["create_server"])
        server = api.create_server("127.0.0.1", 0, str(Path(self.temp_dir.name) / "api.sqlite3"))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/health")) as response:
                self.assertEqual(response.status, 200)
                payload = json.loads(response.read())
            self.assertEqual(payload["status"], "ok")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
