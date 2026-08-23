from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import threading
from unittest.mock import patch
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

from agentweb.alerting import signature
from agentweb.api import create_server
from agentweb.auth import Authenticator, KeyStore
from agentweb.engine import AgentWebEngine
from agentweb.errors import AuthenticationError, PermissionError
from agentweb.fetch import html_to_text
from agentweb.memory import MemoryStore
from agentweb.migrations import _prepare_row, export_sqlite_relational
from agentweb.rdbms import DatabaseConfig, DatabaseConfigurationError
from agentweb.search import JsonSearchProvider, SearchProviderConfig, search
from agentweb.synthesis import synthesize
from agentweb.secrets import MappingSecretProvider, SecretProviderConfig, SecretProviderError
from agentweb.normalizer import normalize
from agentweb.parser import parse
from agentweb.ranking import RankedSource, rank
from agentweb.trust_engine import TrustEngine


class FixtureHandler(BaseHTTPRequestHandler):
    body = b"<html><head><title>Fixture</title><meta name='description' content='A fixture page'></head><body><h1>Hello</h1><p>AgentWeb test content.</p><a href='/next'>Next</a></body></html>"

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_args):
        pass


class AgentWebTests(unittest.TestCase):
    def setUp(self):
        os.environ["AGENTWEB_ALLOW_PRIVATE_TARGETS"] = "1"
        self.fixture = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        self.thread = threading.Thread(target=self.fixture.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.fixture.server_port}/fixture"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.temp_dir.name) / "test.sqlite3")
        self.engine = AgentWebEngine(self.store)

    def tearDown(self):
        os.environ.pop("AGENTWEB_ALLOW_PRIVATE_TARGETS", None)
        os.environ.pop("AGENTWEB_API_KEY", None)
        os.environ.pop("AGENTWEB_API_KEYS", None)
        os.environ.pop("AGENTWEB_CHROMIUM_PATH", None)
        os.environ.pop("AGENTWEB_ENV", None)
        os.environ.pop("AGENTWEB_SECRET_PROVIDER", None)
        os.environ.pop("AGENTWEB_DB_POOL_SIZE", None)
        os.environ.pop("AGENTWEB_SEARCH_PROVIDER", None)
        os.environ.pop("AGENTWEB_SEARCH_ENDPOINT", None)
        os.environ.pop("AGENTWEB_SEARCH_API_KEY", None)
        os.environ.pop("AGENTWEB_SEARCH_TIMEOUT_SECONDS", None)
        self.fixture.shutdown()
        self.fixture.server_close()
        self.temp_dir.cleanup()

    def test_html_to_text_removes_scripts(self):
        self.assertEqual(html_to_text("<p>Hello</p><script>ignore()</script>"), "Hello")

    def test_parser_extracts_title_links_and_json(self):
        document = parse(b"<title>Page</title><p>Hello</p><a href='/next'>Next</a>", "text/html")
        self.assertEqual(document.title, "Page")
        self.assertEqual(document.text, "Hello Next")
        self.assertEqual(document.links, ["/next"])
        self.assertEqual(parse(b'{"a": 1}', "application/json").data, {"a": 1})

    def test_crawler_discovers_same_origin_links(self):
        result = self.engine.crawler.crawl(self.url, max_pages=2, depth=1)
        self.assertEqual(result.pages_crawled, 2)
        self.assertEqual(result.pages[0].depth, 0)
        self.assertEqual(result.pages[1].depth, 1)
        self.assertFalse(result.truncated)

    def test_browser_renders_and_extracts(self):
        session = self.engine.browser_open(
            self.url,
            [
                {"type": "wait_for", "selector": "h1"},
                {"type": "extract", "selector": "h1"},
            ],
        )
        self.assertEqual(session.status, "complete")
        self.assertEqual(session.title, "Fixture")
        self.assertIn("Hello", session.text)
        self.assertEqual(session.extracted[0]["text"], "Hello")

    def test_provider_backed_search_is_injected_and_forwards_freshness(self):
        calls = []

        class FakeProvider:
            def search(self, query, limit=10, freshness=None):
                calls.append((query, limit, freshness))
                return [{"url": "https://example.com/result", "title": "Result", "snippet": "Snippet"}]

        provider = FakeProvider()
        results = search("agentweb", 3, "week", provider)
        self.assertEqual(results[0]["url"], "https://example.com/result")
        self.assertEqual(calls, [("agentweb", 3, "week")])

    def test_json_search_provider_normalizes_aliases_and_auth_header(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, _limit):
                return json.dumps({"results": [{"url": "https://example.com", "description": "A result", "date": "2026-08-24"}]}).encode()

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["authorization"] = request.get_header("Authorization")
            captured["timeout"] = timeout
            return FakeResponse()

        with patch("agentweb.search.urlopen", fake_urlopen):
            results = JsonSearchProvider("https://search.example.test/query", "test-secret", 7.0).search("agentweb", 2, "week")
        self.assertEqual(results[0]["snippet"], "A result")
        self.assertEqual(results[0]["published_at"], "2026-08-24")
        self.assertIn("freshness=week", captured["url"])
        self.assertEqual(captured["authorization"], "Bearer test-secret")
        self.assertEqual(captured["timeout"], 7.0)

    def test_search_provider_configuration_requires_endpoint_for_json_provider(self):
        os.environ["AGENTWEB_SEARCH_PROVIDER"] = "json"
        os.environ.pop("AGENTWEB_SEARCH_ENDPOINT", None)
        with self.assertRaisesRegex(Exception, "ENDPOINT"):
            SearchProviderConfig.from_environment()

    def test_normalizer_preserves_unparseable_values(self):
        price = normalize("₹42,999", "price")
        self.assertEqual(price.value, 42999)
        self.assertEqual(price.currency, "INR")
        self.assertTrue(price.normalized)
        self.assertGreater(price.confidence, normalize("unknown", "price").confidence)
        self.assertFalse(normalize("unknown", "price").normalized)

    def test_trust_engine_blocks_private_by_default_and_allows_explicit_fixture_mode(self):
        os.environ.pop("AGENTWEB_ALLOW_PRIVATE_TARGETS", None)
        self.assertFalse(TrustEngine().should_fetch("http://127.0.0.1:8000").allowed)
        os.environ["AGENTWEB_ALLOW_PRIVATE_TARGETS"] = "1"
        self.assertTrue(TrustEngine().should_fetch("http://127.0.0.1:8000").allowed)

    def test_ranking_orders_sources_by_score(self):
        sources = [
            __import__("agentweb.models", fromlist=["Source"]).Source("a", "https://a.example", trust_score=0.4),
            __import__("agentweb.models", fromlist=["Source"]).Source("b", "https://b.example", trust_score=0.9),
        ]
        self.assertEqual(rank(sources, "research task")[0].source.id, "b")

    def test_snapshot_history_and_diff(self):
        self.assertFalse(self.store.save_snapshot("target", self.url, "first", "now"))
        first = self.store.get_latest("target")
        self.assertFalse(self.store.save_snapshot("target", self.url, "first", "later"))
        self.assertTrue(self.store.save_snapshot("target", self.url, "second", "latest"))
        snapshots = self.store.list_snapshots("target")
        self.assertEqual(len(snapshots), 2)
        result = self.store.diff("target", first["content_hash"], snapshots[-1]["content_hash"])
        self.assertTrue(result["changed"])

    def test_extract_returns_title_and_text(self):
        data = self.engine.extract(self.url)
        self.assertEqual(data["title"], "Fixture")
        self.assertIn("AgentWeb test content", data["text"])
        self.assertEqual(data["links"], ["/next"])
        self.assertGreater(data["trust_score"], 0)
        self.assertEqual(data["field_confidence"]["title"], 0.95)
        self.assertGreater(data["confidence"], 0.5)
        self.assertIn("main text extracted", data["confidence_reasons"])

    def test_schema_guided_extract_returns_normalized_field(self):
        data = self.engine.extract(self.url, {"title": "string"})
        self.assertEqual(data["data"]["title"]["value"], "Fixture")
        self.assertGreaterEqual(data["data"]["title"]["confidence"], 0.8)

    def test_synthesis_surfaces_conflicts_and_structured_comparison(self):
        sources = [
            __import__("agentweb.models", fromlist=["Source"]).Source(
                "src-a", "https://a.example", "Retailer A", "Price $100, in stock", trust_score=0.9
            ),
            __import__("agentweb.models", fromlist=["Source"]).Source(
                "src-b", "https://b.example", "Retailer B", "Price $120, out of stock", trust_score=0.8
            ),
        ]
        result = synthesize(
            [RankedSource(sources[0], 0.9), RankedSource(sources[1], 0.8)],
            "compare prices",
            "comparison",
        )
        self.assertFalse(result.insufficient_evidence)
        self.assertEqual(result.output_format, "comparison")
        self.assertEqual({source.id for source in result.sources if source.cited}, {"src-a", "src-b"})
        self.assertEqual(result.citations[0].source_ids, ["src-a", "src-b"])
        self.assertIn("price", {item["field"] for item in result.conflicts or []})
        self.assertIn("Conflicts", result.answer)

    def test_synthesis_marks_weak_evidence_insufficient(self):
        source = __import__("agentweb.models", fromlist=["Source"]).Source(
            "src-weak", "https://weak.example", "", "", trust_score=0.1
        )
        result = synthesize([RankedSource(source, 0.1, include=False)], "find evidence")
        self.assertTrue(result.insufficient_evidence)
        self.assertEqual(result.citations, [])
        self.assertFalse(result.sources[0].cited)

    def test_solve_supports_json_output_format(self):
        response = self.engine.solve(f"Summarize {self.url}", mode="focus", output_format="json")
        self.assertEqual(response.output_format, "json")
        self.assertIsInstance(response.structured_output, dict)
        self.assertFalse(response.insufficient_evidence)
        self.assertTrue(response.citations)

    def test_solve_direct_url_returns_citation_and_trace(self):
        response = self.engine.solve(f"Summarize {self.url}", mode="focus")
        self.assertEqual(response.mode, "focus")
        self.assertEqual(len(response.sources), 1)
        self.assertEqual(response.citations[0].source_ids, [response.sources[0].id])
        trace = self.engine.traces.get(response.execution_id)
        self.assertIsNotNone(trace)
        self.assertTrue(any(span["component"] == "synthesis" for span in trace["spans"]))

    def test_monitor_lifecycle_and_snapshot_reuse(self):
        monitor = self.engine.create_monitor(f"Watch {self.url}", "hourly")
        first = self.engine.check_monitor(monitor)
        self.assertEqual(first.last_event, "no_change")
        FixtureHandler.body = b"<html><title>Changed</title><body>changed</body></html>"
        second = self.engine.check_monitor(first)
        self.assertEqual(second.last_event, "change_detected")
        self.assertIsNotNone(second.last_change_at)
        self.assertTrue(self.store.delete_monitor(monitor.id))
        FixtureHandler.body = b"<html><head><title>Fixture</title></head><body>restored</body></html>"

    def test_monitor_unreachable_is_check_failed(self):
        monitor = self.engine.create_monitor("Watch http://127.0.0.1:1/unreachable", "daily")
        result = self.engine.check_monitor(monitor)
        self.assertEqual(result.last_event, "check_failed")
        self.assertIsNotNone(result.last_error)

    def test_scheduler_runs_due_monitor_and_reschedules(self):
        monitor = self.engine.create_monitor(f"Watch {self.url}", "hourly")
        now = time.time() + 1
        result = self.engine.scheduler.run_once(now=now)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["monitor_id"], monitor.id)
        job = self.store.list_jobs()[0]
        self.assertEqual(job["status"], "pending")
        self.assertEqual(job["attempts"], 0)
        self.assertGreater(job["run_at"], now)

    def test_scheduler_prioritizes_minutely_monitor(self):
        daily = self.engine.create_monitor(f"Daily {self.url}", "daily")
        minutely = self.engine.create_monitor(f"Minutely {self.url}", "minutely")
        result = self.engine.scheduler.run_once(now=time.time() + 1)
        self.assertEqual(result["monitor_id"], minutely.id)
        self.assertNotEqual(result["monitor_id"], daily.id)

    def test_scheduler_moves_repeated_failures_to_dead_letter(self):
        monitor = self.engine.create_monitor(f"Watch {self.url}", "hourly")
        job = self.store.list_jobs()[0]
        base = time.time() + 1
        for attempt in range(5):
            now = base + (attempt * 60)
            claimed = self.store.claim_due_job(now=now, lease_seconds=1)
            self.assertIsNotNone(claimed)
            status = self.store.fail_job(job["id"], "temporary failure", now=now)
            if attempt < 4:
                self.assertEqual(status, "pending")
        self.assertEqual(self.store.get_job(job["id"])["status"], "dead_letter")

    def test_webhook_signature_is_deterministic(self):
        body = b'{"ok":true}'
        expected_digest = hmac.new(b"secret", b"1700000000." + body, hashlib.sha256).hexdigest()
        self.assertEqual(signature(body, "1700000000", "secret"), f"t=1700000000,v1={expected_digest}")

    def test_external_secret_mapping_and_production_fail_closed_policy(self):
        provider = MappingSecretProvider({"DATABASE_URL": "postgresql://db.example/agentweb"}, ttl_seconds=0)
        self.assertEqual(provider.get("DATABASE_URL"), "postgresql://db.example/agentweb")
        os.environ["AGENTWEB_ENV"] = "production"
        os.environ["AGENTWEB_SECRET_PROVIDER"] = "env"
        with self.assertRaises(SecretProviderError):
            SecretProviderConfig.from_environment()
        os.environ["AGENTWEB_SECRET_PROVIDER"] = "mapping"
        config = DatabaseConfig.from_environment(provider)
        self.assertEqual(config.driver, "postgres")
        self.assertEqual(config.pool_size, 4)

    def test_production_database_requires_postgresql_url(self):
        os.environ["AGENTWEB_ENV"] = "production"
        os.environ["AGENTWEB_SECRET_PROVIDER"] = "mapping"
        with self.assertRaises(DatabaseConfigurationError):
            DatabaseConfig.from_environment(MappingSecretProvider({"DATABASE_URL": "sqlite:///unsafe.db"}))

    def test_relational_export_is_dry_run_and_checksumed(self):
        self.engine.create_monitor(f"Watch {self.url}", "daily", org_id="org-a")
        output = Path(self.temp_dir.name) / "migration"
        manifest = export_sqlite_relational(self.store.path, output, dry_run=True)
        self.assertEqual(manifest["format"], "agentweb-relational-export-v1")
        self.assertFalse(output.exists())
        self.assertTrue(any(item["table"] == "api_keys" for item in manifest["tables"]))
        self.assertTrue(any(item["table"] == "audit_events" for item in manifest["tables"]))
        self.assertTrue(any(item["table"] == "scheduler_jobs" for item in manifest["tables"]))
        self.assertFalse(manifest["destructive"])

    def test_relational_import_prepares_legacy_defaults_and_rejects_missing_identity(self):
        row = {
            "id": "mon-1",
            "org_id": "org-a",
            "task": "watch",
            "status": "active",
            "frequency": "daily",
        }
        prepared = _prepare_row("monitors", row)
        self.assertIsNotNone(prepared[7])
        self.assertIsNotNone(getattr(prepared[7], "tzinfo", None))
        with self.assertRaisesRegex(ValueError, "organizations"):
            _prepare_row("organizations", {"id": "org-a", "name": None})

    def test_authenticator_enforces_scopes(self):
        os.environ["AGENTWEB_API_KEYS"] = json.dumps({"test-key": ["search:read"]})
        authenticator = Authenticator()
        with self.assertRaises(AuthenticationError):
            authenticator.authenticate(None, "search:read")
        with self.assertRaises(PermissionError):
            authenticator.authenticate("Bearer test-key", "solve:execute")
        self.assertEqual(authenticator.authenticate("Bearer test-key", "search:read").key_id, "test-key"[:8])

    def test_health_and_report_endpoints(self):
        server = create_server("127.0.0.1", 0, str(Path(self.temp_dir.name) / "api.sqlite3"))
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

    def test_http_crawl_route_returns_bounded_pages(self):
        server = create_server("127.0.0.1", 0, str(Path(self.temp_dir.name) / "crawl.sqlite3"))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            body = json.dumps({"start_url": self.url, "max_pages": 2, "depth": 1}).encode()
            request = Request(
                f"http://127.0.0.1:{server.server_port}/crawl",
                data=body,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urlopen(request) as response:
                payload = json.loads(response.read())
            self.assertEqual(payload["pages_crawled"], 2)
            self.assertFalse(payload["truncated"])
        finally:
            server.shutdown()
            server.server_close()

    def test_http_browser_route_returns_rendered_session(self):
        os.environ["AGENTWEB_CHROMIUM_PATH"] = "/usr/bin/chromium"
        server = create_server("127.0.0.1", 0, str(Path(self.temp_dir.name) / "browser.sqlite3"))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            body = json.dumps({"url": self.url, "actions": [{"type": "extract", "selector": "h1"}]}).encode()
            request = Request(
                f"http://127.0.0.1:{server.server_port}/browser/sessions",
                data=body,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urlopen(request) as response:
                payload = json.loads(response.read())
            self.assertEqual(payload["status"], "complete")
            self.assertEqual(payload["extracted"][0]["text"], "Hello")
        finally:
            server.shutdown()
            server.server_close()

    def test_tenant_isolation_hides_monitor_and_trace_from_other_org(self):
        data_path = Path(self.temp_dir.name) / "tenants.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        admin_a = server.authenticator.key_store.create_key("org-a", ["admin:*"])["secret"]
        admin_b = server.authenticator.key_store.create_key("org-b", ["admin:*"])["secret"]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            monitor_body = json.dumps({"task": f"Watch {self.url}", "frequency": "daily"}).encode()
            request = Request(
                f"http://127.0.0.1:{server.server_port}/observe",
                data=monitor_body,
                method="POST",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {admin_a}"},
            )
            with urlopen(request) as response:
                monitor = json.loads(response.read())
            monitor_id = monitor["id"]
            solve = server.engine.solve(f"Summarize {self.url}", org_id="org-a")
            self.assertIsNotNone(server.engine.traces.get(solve.execution_id, "org-a"))
            self.assertIsNone(server.engine.traces.get(solve.execution_id, "org-b"))
            cross_request = Request(
                f"http://127.0.0.1:{server.server_port}/observe/{monitor_id}",
                headers={"Authorization": f"Bearer {admin_b}"},
            )
            with self.assertRaises(Exception) as context:
                urlopen(cross_request)
            self.assertIn("404", str(context.exception))
            response = server.authenticator.key_store.list_audit("org-a")
            self.assertTrue(any(event["action"] == "api_key.created" for event in response))
            self.assertFalse(any(admin_a in json.dumps(event) for event in response))
        finally:
            server.shutdown()
            server.server_close()

    def test_persistent_keys_are_hashed_and_admin_listing_is_redacted(self):
        data_path = Path(self.temp_dir.name) / "keys.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        root = server.authenticator.key_store.create_key("org-a", ["admin:*"])["secret"]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            body = json.dumps({"scopes": ["search:read"]}).encode()
            request = Request(
                f"http://127.0.0.1:{server.server_port}/admin/keys",
                data=body,
                method="POST",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {root}"},
            )
            with urlopen(request) as response:
                created = json.loads(response.read())
            self.assertTrue(created["secret"].startswith("sk-live-"))
            listing_request = Request(
                f"http://127.0.0.1:{server.server_port}/admin/keys",
                headers={"Authorization": f"Bearer {root}"},
            )
            with urlopen(listing_request) as response:
                listing = json.loads(response.read())
            self.assertTrue(all("secret" not in key for key in listing["keys"]))
            with __import__("sqlite3").connect(data_path) as connection:
                stored = connection.execute("SELECT hashed_secret FROM api_keys WHERE id=?", (created["id"],)).fetchone()[0]
            self.assertNotEqual(stored, created["secret"])
            self.assertNotIn(created["secret"], stored)
        finally:
            server.shutdown()
            server.server_close()

    def test_admin_revocation_is_organization_scoped_and_invalidates_key(self):
        data_path = Path(self.temp_dir.name) / "revoke.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        admin = server.authenticator.key_store.create_key("org-a", ["admin:*"])["secret"]
        other = server.authenticator.key_store.create_key("org-b", ["search:read"])
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            revoke_other = Request(
                f"http://127.0.0.1:{server.server_port}/admin/keys/{other['id']}",
                method="DELETE",
                headers={"Authorization": f"Bearer {admin}"},
            )
            with self.assertRaises(Exception) as context:
                urlopen(revoke_other)
            self.assertIn("404", str(context.exception))
            own = server.authenticator.key_store.create_key("org-a", ["search:read"])
            revoke_own = Request(
                f"http://127.0.0.1:{server.server_port}/admin/keys/{own['id']}",
                method="DELETE",
                headers={"Authorization": f"Bearer {admin}"},
            )
            with urlopen(revoke_own) as response:
                self.assertEqual(response.status, 204)
            with self.assertRaises(Exception):
                urlopen(Request(
                    f"http://127.0.0.1:{server.server_port}/search",
                    data=b'{"query":"test"}',
                    method="POST",
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {own['secret']}"},
                ))
        finally:
            server.shutdown()
            server.server_close()

    def test_http_idempotency_replays_and_conflicts(self):
        data_path = Path(self.temp_dir.name) / "idempotency.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        admin = server.authenticator.key_store.create_key("org-a", ["admin:*"])["secret"]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            body = json.dumps({"task": f"Summarize {self.url}", "mode": "flash", "idempotency_key": "solve-1"}).encode()
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {admin}"}
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/solve", data=body, method="POST", headers=headers)) as response:
                first = json.loads(response.read())
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/solve", data=body, method="POST", headers=headers)) as response:
                replay = json.loads(response.read())
            self.assertEqual(first["execution_id"], replay["execution_id"])
            conflict_body = json.dumps({"task": "different", "mode": "flash", "idempotency_key": "solve-1"}).encode()
            with self.assertRaises(Exception) as context:
                urlopen(Request(f"http://127.0.0.1:{server.server_port}/solve", data=conflict_body, method="POST", headers=headers))
            self.assertIn("409", str(context.exception))
        finally:
            server.shutdown()
            server.server_close()

    def test_http_usage_and_cursor_paginated_monitors(self):
        data_path = Path(self.temp_dir.name) / "usage.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        admin = server.authenticator.key_store.create_key("org-a", ["admin:*"])["secret"]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {admin}"}
            for suffix in ("/one", "/two"):
                body = json.dumps({"task": f"Watch {self.url}{suffix}", "frequency": "daily"}).encode()
                with urlopen(Request(f"http://127.0.0.1:{server.server_port}/observe", data=body, method="POST", headers=headers)):
                    pass
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/observe?limit=1", headers=headers)) as response:
                first_page = json.loads(response.read())
            self.assertEqual(len(first_page["data"]), 1)
            self.assertTrue(first_page["has_more"])
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/observe?limit=1&cursor={first_page['next_cursor']}", headers=headers)) as response:
                second_page = json.loads(response.read())
            self.assertEqual(len(second_page["data"]), 1)
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/solve", data=json.dumps({"task": f"Summarize {self.url}", "mode": "focus"}).encode(), method="POST", headers=headers)):
                pass
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/admin/usage", headers=headers)) as response:
                usage = json.loads(response.read())
            self.assertEqual(usage["requests_by_mode"]["focus"], 1)
            self.assertEqual(usage["requests_by_mode"]["flash"], 0)
            with self.assertRaises(Exception) as period_error:
                urlopen(Request(f"http://127.0.0.1:{server.server_port}/admin/usage?period=bad", headers=headers))
            self.assertIn("400", str(period_error.exception))
            with self.assertRaises(Exception) as cursor_error:
                urlopen(Request(f"http://127.0.0.1:{server.server_port}/observe?cursor=not-valid", headers=headers))
            self.assertIn("400", str(cursor_error.exception))
        finally:
            server.shutdown()
            server.server_close()

    def test_http_scope_auth_rejects_missing_scope(self):
        os.environ["AGENTWEB_API_KEYS"] = json.dumps({"search-only": ["search:read"]})
        server = create_server("127.0.0.1", 0, str(Path(self.temp_dir.name) / "auth.sqlite3"))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            body = b'{"task":"test"}'
            request = Request(
                f"http://127.0.0.1:{server.server_port}/solve",
                data=body,
                method="POST",
                headers={"Content-Type": "application/json", "Authorization": "Bearer search-only"},
            )
            with self.assertRaises(Exception) as context:
                urlopen(request)
            self.assertIn("403", str(context.exception))
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
