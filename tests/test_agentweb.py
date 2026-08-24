from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import tempfile
import threading
from unittest.mock import patch
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agentweb.alerting import DeliveryResult, signature
from agentweb.api import create_server
from agentweb.auth import Authenticator, KeyStore, RateLimiter
from agentweb.browser import BrowserEngine
from agentweb.credentials import BrowserCredentialStore
from agentweb.engine import AgentWebEngine
from agentweb.errors import AuthenticationError, BrowserUnavailableError, PermissionError
from agentweb.fetch import html_to_text
from agentweb.memory import MemoryStore
from agentweb.maintenance import purge_retention
from agentweb.metrics import MetricStore, MetricsRegistry, PostgresMetricStore
from agentweb.migrations import _prepare_row, export_sqlite_relational
from agentweb.rdbms import DatabaseConfig, DatabaseConfigurationError, POSTGRES_SCHEMA, PostgresDistributedQueue, open_distributed_queue
from agentweb.trace import Span
from agentweb.search import JsonSearchProvider, SearchProviderConfig, search
from agentweb.scheduler import Scheduler
from agentweb.synthesis import synthesize
from agentweb.secrets import MappingSecretProvider, SecretProviderConfig, SecretProviderError
from cryptography.fernet import Fernet
from agentweb.normalizer import normalize
from agentweb.parser import parse
from agentweb.ranking import RankedSource, rank
from agentweb.trust_engine import TrustEngine
from agentweb.redaction import redact_text


class FixtureHandler(BaseHTTPRequestHandler):
    default_body = b"<html><head><title>Fixture</title><meta name='description' content='A fixture page'></head><body><h1>Hello</h1><p>AgentWeb test content.</p><a href='/next'>Next</a></body></html>"
    body = default_body

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_args):
        pass


def start_test_server(server: ThreadingHTTPServer) -> threading.Thread:
    server.daemon_threads = False
    server.block_on_close = True
    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.01},
        daemon=True,
    )
    thread.start()
    return thread


def stop_test_server(server: ThreadingHTTPServer, thread: threading.Thread) -> None:
    server.shutdown()
    thread.join(timeout=1.0)
    server.server_close()


class AgentWebTests(unittest.TestCase):
    def setUp(self):
        os.environ["AGENTWEB_ALLOW_PRIVATE_TARGETS"] = "1"
        FixtureHandler.body = FixtureHandler.default_body
        self.fixture = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        self.thread = start_test_server(self.fixture)
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
        os.environ.pop("AGENTWEB_BROWSER_CREDENTIAL_KEY", None)
        FixtureHandler.body = FixtureHandler.default_body
        stop_test_server(self.fixture, self.thread)
        self.temp_dir.cleanup()

    def test_html_to_text_removes_scripts(self):
        self.assertEqual(html_to_text("<p>Hello</p><script>ignore()</script>"), "Hello")

    def test_parser_extracts_tables_and_entities(self):
        document = parse(b"<h1>Acme Corp</h1><table><tr><th>Product</th><th>Price</th></tr><tr><td>Widget</td><td>$10</td></tr></table>", "text/html")
        self.assertEqual(document.tables, [[['Product', 'Price'], ['Widget', '$10']]])
        self.assertIn("Acme Corp", document.entities)

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

    def test_browser_credentials_are_encrypted_scoped_and_revocable(self):
        key = Fernet.generate_key().decode()
        store = BrowserCredentialStore(Path(self.temp_dir.name) / "credentials.sqlite3", MappingSecretProvider({"AGENTWEB_BROWSER_CREDENTIAL_KEY": key}))
        created = store.create("org-a", "shop", "alice@example.com", "password-123", "operator")
        self.assertNotIn("password-123", json.dumps(created))
        self.assertEqual(store.resolve("org-a", created["id"]), {"username": "alice@example.com", "secret": "password-123"})
        self.assertIsNone(store.resolve("org-b", created["id"]))
        self.assertNotIn("password-123", json.dumps(store.list("org-a")))
        with sqlite3.connect(store.path) as connection:
            encrypted = connection.execute("SELECT encrypted_secret FROM browser_credentials WHERE id=?", (created["id"],)).fetchone()[0]
        self.assertNotEqual(encrypted, "password-123")
        self.assertTrue(store.revoke("org-a", created["id"], "operator"))
        self.assertIsNone(store.resolve("org-a", created["id"]))

    def test_browser_credential_action_scrubs_values_from_rendered_output(self):
        original = FixtureHandler.body
        FixtureHandler.body = b"<html><body><form><input id='username'><input id='password' type='password'></form></body></html>"
        os.environ["AGENTWEB_CHROMIUM_PATH"] = "/usr/bin/chromium"
        key = Fernet.generate_key().decode()
        engine = AgentWebEngine(self.store, secret_provider=MappingSecretProvider({"AGENTWEB_BROWSER_CREDENTIAL_KEY": key}))
        created = engine.credentials.create("development", "fixture", "alice@example.com", "password-123", "operator")
        try:
            session = engine.browser_open(
                self.url,
                [{"type": "fill_credential", "selector": "#username", "field": "username"}, {"type": "fill_credential", "selector": "#password", "field": "secret"}],
                "development",
                created["id"],
            )
            self.assertEqual(session.status, "complete")
            self.assertNotIn("alice@example.com", json.dumps(session.to_dict()))
            self.assertNotIn("password-123", json.dumps(session.to_dict()))
        finally:
            FixtureHandler.body = original

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

    def test_normalizer_handles_locale_price_formats(self):
        self.assertEqual(normalize("€1.234,56", "price").value, 1234.56)
        self.assertEqual(normalize("1 234,50 EUR", "price").currency, "EUR")
        self.assertEqual(normalize("1 234,50 EUR", "price").value, 1234.50)
        self.assertEqual(normalize("(£2,000.00)", "price").value, -2000)
        self.assertEqual(normalize("Rs 12,34,567", "price").value, 1234567)
        self.assertEqual(normalize("USD 1,234.50", "price").currency, "USD")

    def test_normalizer_handles_locale_date_formats(self):
        self.assertEqual(normalize("31/12/2025", "date").value, "2025-12-31")
        self.assertEqual(normalize("12/31/2025", "date").value, "2025-12-31")
        self.assertEqual(normalize("15 août 2025", "date").value, "2025-08-15")
        self.assertEqual(normalize("15 agosto 2025", "date").value, "2025-08-15")
        self.assertEqual(normalize("31. März 2025", "date").value, "2025-03-31")
        self.assertFalse(normalize("31/31/2025", "date").normalized)

    def test_safe_url_validation_rejects_credentials_and_redirects_are_rechecked(self):
        os.environ.pop("AGENTWEB_ALLOW_PRIVATE_TARGETS", None)
        with self.assertRaisesRegex(ValueError, "credentials"):
            __import__("agentweb.fetch", fromlist=["validate_url"]).validate_url("https://user:secret@example.com/path")
        self.assertFalse(TrustEngine().should_fetch("https://user:secret@example.com/path").allowed)

    def test_diagnostic_redaction_removes_embedded_secrets(self):
        value = "Authorization: Bearer sk-live-super-secret https://example.test/hook?token=hidden"
        redacted = redact_text(value)
        self.assertNotIn("super-secret", redacted)
        self.assertNotIn("hidden", redacted)
        self.assertIn("[REDACTED]", redacted)

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

    def test_nullable_monitor_policy_is_accepted_by_relational_row_preparation(self):
        row = {
            "id": "monitor-1",
            "org_id": "org-a",
            "task": "watch",
            "status": "active",
            "frequency": "hourly",
            "target_url": "https://example.com",
            "webhook_url": None,
            "created_at": 1_800_000_000,
            "last_checked_at": None,
            "last_change_at": None,
            "last_event": None,
            "last_error": None,
            "last_delivery_id": None,
            "last_delivery_status": None,
            "last_delivery_attempts": 0,
            "last_delivery_error": None,
            "change_policy_json": None,
        }
        prepared = _prepare_row("monitors", row)
        self.assertIsNone(prepared[-1])

    def test_audit_filters_time_ranges_and_retention_are_organization_scoped(self):
        audit = KeyStore(Path(self.temp_dir.name) / "audit.sqlite3")
        started = time.time()
        audit.audit("org-a", "operator", "config.changed", "monitor-1", {"safe": True})
        audit.audit("org-a", "other", "api_key.created", "key-1", {})
        audit.audit("org-b", "operator", "config.changed", "monitor-2", {})
        filtered = audit.list_audit("org-a", action="config.changed", actor="operator", target="monitor-1", since=started - 1, until=time.time() + 1)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["org_id"], "org-a")
        self.assertEqual(filtered[0]["metadata"], {"safe": True})
        self.assertEqual(audit.list_audit("org-a", action="config.changed", actor="operator", target="monitor-2"), [])
        with sqlite3.connect(audit.path) as connection:
            connection.execute("UPDATE audit_events SET timestamp=? WHERE target=?", (1.0, "monitor-1"))
        result = purge_retention(self.store, self.engine.traces, audit_store=audit, audit_retention_days=1, now=100_000, org_id="org-a")
        self.assertEqual(result["deleted_audit"], 1)
        remaining = audit.list_audit("org-a")
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["target"], "key-1")
        self.assertEqual(len(audit.list_audit("org-b")), 1)

    def test_audit_page_is_bounded_and_uses_filter_index(self):
        audit = KeyStore(Path(self.temp_dir.name) / "audit-page.sqlite3")
        for index in range(4):
            audit.audit("org-a", "operator", "config.changed", f"monitor-{index}", {"index": index})
        first, has_more = audit.list_audit_page("org-a", limit=2, offset=0, action="config.changed")
        second, second_has_more = audit.list_audit_page("org-a", limit=2, offset=2, action="config.changed")
        self.assertEqual(len(first), 2)
        self.assertTrue(has_more)
        self.assertEqual(len(second), 2)
        self.assertFalse(second_has_more)
        self.assertEqual({event["id"] for event in first}.isdisjoint(event["id"] for event in second), True)
        with sqlite3.connect(audit.path) as connection:
            plan = connection.execute(
                "EXPLAIN QUERY PLAN SELECT id FROM audit_events WHERE org_id=? AND action=? ORDER BY timestamp DESC, id DESC LIMIT ? OFFSET ?",
                ("org-a", "config.changed", 2, 0),
            ).fetchall()
        self.assertTrue(any("idx_audit_org_action_time" in str(row) for row in plan), plan)

    def test_durable_metrics_persist_filter_and_purge_by_organization(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.sqlite3"
            first = MetricsRegistry(MetricStore(path))
            first.increment("request_count", labels={"endpoint": "/solve", "org_id": "org-a"})
            first.increment("request_count", labels={"endpoint": "/solve", "org_id": "org-b"})
            first.increment("process_health", labels=None)
            first.gauge("queue_due", 3, {"org_id": "org-a"})
            second = MetricsRegistry(MetricStore(path))
            visible = second.snapshot("org-a")
            self.assertIn("request_count{endpoint=/solve,org_id=org-a}", visible["counters"])
            self.assertNotIn("request_count{endpoint=/solve,org_id=org-b}", visible["counters"])
            self.assertNotIn("process_health", visible["counters"])
            self.assertIn("process_health", second.snapshot()["counters"])
            self.assertEqual(visible["gauges"]["queue_due{org_id=org-a}"], 3.0)
            self.assertGreaterEqual(second.purge_expired(0, now=time.time() + 1, org_id="org-a"), 2)
            self.assertNotIn("request_count{endpoint=/solve,org_id=org-a}", second.snapshot("org-a")["counters"])

    def test_memory_reuse_retention_and_trace_deletion(self):
        from datetime import datetime, timezone
        now = 1_800_000_000.0
        fresh_at = datetime.fromtimestamp(now - 60, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        old_at = datetime.fromtimestamp(now - 200, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        self.store.snapshot("target", "old", old_at, "org-a")
        self.store.snapshot("target", "fresh", fresh_at, "org-a")
        self.assertEqual(self.store.reusable_snapshot("target", "org-a", 120, now)["content"], "fresh")
        self.assertEqual(self.store.purge_expired_snapshots(100, now, "org-a"), 1)
        self.engine.traces.save("exec-a", [Span("test", "save", 0, 1, "token=hidden", "https://example.test/?secret=hidden")], org_id="org-a")
        stored = self.engine.traces.get("exec-a", "org-a")
        self.assertNotIn("hidden", json.dumps(stored))
        self.assertEqual(self.engine.traces.delete("org-a", "exec-a"), 1)
        self.assertIsNone(self.engine.traces.get("exec-a", "org-a"))
        self.store.enqueue_webhook_delivery("org-a", "mon-a", "https://example.test/hook?token=hidden", {"event": "change"})
        debug = self.store.export_debug("org-a")
        self.assertNotIn("hidden", json.dumps(debug))
        self.assertGreaterEqual(self.store.queue_summary("org-a")["pending"], 1)
        self.assertEqual(self.store.queue_summary("org-b").get("pending", 0), 0)

    def test_ranking_consumes_recency_and_extraction_confidence(self):
        from agentweb.models import Source
        newer = Source("new", "https://new.example", "Fresh", "current", trust_score=0.6, published_at="2099-01-01T00:00:00Z", content_type="text/html", extraction_confidence=1.0)
        older = Source("old", "https://old.example", "Old", "current", trust_score=0.6, published_at="2020-01-01T00:00:00Z", content_type="application/octet-stream", extraction_confidence=0.1)
        self.assertEqual(rank([older, newer], "current")[0].source.id, "new")

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
        self.assertTrue(result.citations)
        self.assertTrue(all(item.claim_span[1] > item.claim_span[0] and item.source_ids for item in result.citations))
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

    def test_synthesis_includes_structured_source_evidence(self):
        original = FixtureHandler.body
        FixtureHandler.body = b"<html><title>Widget Catalog</title><body><table><tr><th>Item</th><th>Price</th></tr><tr><td>Alpha</td><td>$10</td></tr></table><p>Acme Corporation available</p></body></html>"
        try:
            response = self.engine.solve(f"Summarize {self.url}", mode="focus")
            self.assertIn("table 1", response.answer)
            self.assertTrue(response.sources[0].structured_data)
            self.assertTrue(any(response.sources[0].id in citation.source_ids for citation in response.citations))
        finally:
            FixtureHandler.body = original

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

    def test_monitor_change_policy_threshold_is_persisted_and_enforced(self):
        FixtureHandler.body = b"<html><body>Widget price $100. Stable description.</body></html>"
        monitor = self.engine.create_monitor(f"Watch price for {self.url}", "hourly", change_policy={"kind": "price", "absolute_delta": 5})
        self.assertEqual(self.store.get_monitor(monitor.id, "development").change_policy["absolute_delta"], 5.0)
        self.assertEqual(self.engine.check_monitor(monitor).last_event, "no_change")
        FixtureHandler.body = b"<html><body>Widget price $103. Stable description.</body></html>"
        self.assertEqual(self.engine.check_monitor(monitor).last_event, "no_change")
        FixtureHandler.body = b"<html><body>Widget price $110. Stable description.</body></html>"
        self.assertEqual(self.engine.check_monitor(monitor).last_event, "change_detected")
        FixtureHandler.body = b"<html><head><title>Fixture</title></head><body>restored</body></html>"

    def test_monitor_change_policy_relative_availability_and_whitespace_rules(self):
        meaningful = self.engine._meaningful_change
        self.assertFalse(meaningful("watch price", "Price $100", "Price $105", {"kind": "price", "relative_delta_percent": 10})[0])
        self.assertTrue(meaningful("watch price", "Price $100", "Price $111", {"kind": "price", "relative_delta_percent": 10})[0])
        self.assertFalse(meaningful("watch availability", "Item in stock", "Item in stock", {"kind": "availability", "required_state": "in stock"})[0])
        self.assertTrue(meaningful("watch availability", "Item out of stock", "Item in stock", {"kind": "availability", "required_state": "in stock"})[0])
        self.assertFalse(meaningful("watch page", "A   B", "A B", {"kind": "full_content", "ignore_whitespace": True})[0])
        self.assertTrue(meaningful("watch page", "A B", "A C", {"kind": "full_content", "ignore_whitespace": True})[0])

    def test_monitor_task_aware_price_policy_ignores_irrelevant_changes(self):
        FixtureHandler.body = b"<html><body>Widget price $10. Stable description.</body></html>"
        monitor = self.engine.create_monitor(f"Watch price for {self.url}", "hourly")
        first = self.engine.check_monitor(monitor)
        self.assertEqual(first.last_event, "no_change")
        FixtureHandler.body = b"<html><body>Widget price $10. Different navigation text.</body></html>"
        second = self.engine.check_monitor(first)
        self.assertEqual(second.last_event, "no_change")
        FixtureHandler.body = b"<html><body>Widget price $11. Different navigation text.</body></html>"
        third = self.engine.check_monitor(second)
        self.assertEqual(third.last_event, "change_detected")
        FixtureHandler.body = b"<html><head><title>Fixture</title></head><body>restored</body></html>"

    def test_monitor_unreachable_is_check_failed(self):
        monitor = self.engine.create_monitor("Watch http://127.0.0.1:1/unreachable", "daily")
        result = self.engine.check_monitor(monitor)
        self.assertEqual(result.last_event, "check_failed")
        self.assertIsNotNone(result.last_error)

    def test_scheduler_lease_token_blocks_stale_worker_after_reclaim(self):
        monitor = self.engine.create_monitor(f"Watch {self.url}", "hourly")
        first = self.store.claim_due_job(time.time(), lease_seconds=1, org_id="development")
        self.assertIsNotNone(first)
        second = self.store.claim_due_job(time.time() + 2, lease_seconds=1, org_id="development")
        self.assertIsNotNone(second)
        self.assertNotEqual(first["lease_token"], second["lease_token"])
        self.assertFalse(self.store.acknowledge_job(first["id"], "hourly", time.time() + 2, "development", first["lease_token"]))
        self.assertTrue(self.store.acknowledge_job(second["id"], "hourly", time.time() + 2, "development", second["lease_token"]))

    def test_scheduler_routes_claims_and_limits_through_coordinator(self):
        monitor = self.engine.create_monitor(f"Watch {self.url}", "hourly")
        store = self.store

        class Coordinator:
            def __init__(self):
                self.claimed = False
                self.limited = False
                self.acknowledged = False

            def claim_due_job(self, now, lease_seconds):
                self.claimed = True
                return store.claim_due_job(now, lease_seconds, "development")

            def consume_rate_limit(self, org_id, bucket, cost, capacity, refill_per_second):
                self.limited = self.limited or (org_id == "development" and bucket == "scheduled")
                return {"remaining": capacity - cost, "reset": 0.0}

            def acknowledge_job(self, job_id, frequency, now, org_id, lease_token):
                self.acknowledged = True
                return store.acknowledge_job(job_id, frequency, now, org_id, lease_token)

            def fail_job(self, *args, **kwargs):
                return store.fail_job(*args, **kwargs)

            def cancel_job(self, *args, **kwargs):
                return store.cancel_job(*args, **kwargs)

        coordinator = Coordinator()
        scheduler = Scheduler(store, self.engine.check_monitor, coordinator=coordinator)
        result = scheduler.run_once(now=time.time() + 1)
        self.assertEqual(result["status"], "succeeded")
        self.assertTrue(coordinator.claimed)
        self.assertTrue(coordinator.limited)
        self.assertTrue(coordinator.acknowledged)

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

    def test_webhook_delivery_is_queued_and_delivered_once(self):
        self.engine.secret_provider = MappingSecretProvider({"WEBHOOK_SIGNING_KEY": "local-test-signing-key"}, ttl_seconds=0)
        deliveries = []

        def sender(delivery):
            deliveries.append(delivery)
            return DeliveryResult(True, 1, status_code=204)

        self.engine.scheduler.webhook_sender = sender
        monitor = self.engine.create_monitor(f"Watch {self.url}", "hourly", "http://127.0.0.1:9/webhook")
        self.engine.check_monitor(monitor)
        FixtureHandler.body = b"<html><title>Changed</title><body>changed</body></html>"
        changed = self.engine.check_monitor(monitor)
        self.assertEqual(changed.last_delivery_status, "pending")
        delivery_job = next(job for job in self.store.list_jobs("pending", "development") if job["job_type"] == "webhook_delivery")
        check_job = next(job for job in self.store.list_jobs("pending", "development") if job["job_type"] == "monitor_check")
        self.store.cancel_job(check_job["id"], "development")
        result = self.engine.scheduler.run_once(time.time() + 1)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(len(deliveries), 1)
        refreshed = self.store.get_monitor(monitor.id, "development")
        self.assertEqual(refreshed.last_delivery_status, "delivered")
        self.assertEqual(refreshed.last_delivery_attempts, 1)
        self.assertEqual(self.store.get_webhook_delivery(delivery_job["id"], "development")["status"], "delivered")
        FixtureHandler.body = b"<html><head><title>Fixture</title></head><body>restored</body></html>"

    def test_webhook_delivery_failures_dead_letter_and_surface_on_poll(self):
        self.engine.secret_provider = MappingSecretProvider({"WEBHOOK_SIGNING_KEY": "local-test-signing-key"}, ttl_seconds=0)
        self.engine.scheduler.webhook_sender = lambda _delivery: DeliveryResult(False, 1, status_code=503, error="receiver unavailable")
        monitor = self.engine.create_monitor(f"Watch {self.url}", "hourly", "http://127.0.0.1:9/webhook")
        self.engine.check_monitor(monitor)
        FixtureHandler.body = b"<html><title>Changed</title><body>changed</body></html>"
        self.engine.check_monitor(monitor)
        check_job = next(job for job in self.store.list_jobs("pending", "development") if job["job_type"] == "monitor_check")
        self.store.cancel_job(check_job["id"], "development")
        now = time.time() + 1
        result = None
        for _ in range(5):
            result = self.engine.scheduler.run_once(now)
            job = self.store.get_job(next(item["id"] for item in self.store.list_jobs("pending", "development") if item["job_type"] == "webhook_delivery"), "development") if result["status"] != "dead_letter" else None
            now = (job["run_at"] + 1) if job else now + 60
        self.assertEqual(result["status"], "dead_letter")
        refreshed = self.store.get_monitor(monitor.id, "development")
        self.assertEqual(refreshed.last_delivery_status, "dead_letter")
        self.assertEqual(refreshed.last_delivery_attempts, 5)
        self.assertEqual(len(self.store.export_debug("development")["webhook_attempts"]), 5)
        FixtureHandler.body = b"<html><head><title>Fixture</title></head><body>restored</body></html>"

    def test_webhook_delivery_rate_limit_is_organization_scoped(self):
        self.engine.scheduler.webhook_limiter = RateLimiter(capacity=1.0, refill_per_second=0.0)
        delivered = []
        self.engine.scheduler.webhook_sender = lambda delivery: delivered.append(delivery) or DeliveryResult(True, 1, status_code=204)
        first_job = self.store.enqueue_webhook_delivery("development", "mon-first", "http://127.0.0.1:9/one", {"event": "one"})
        second_job = self.store.enqueue_webhook_delivery("development", "mon-second", "http://127.0.0.1:9/two", {"event": "two"})
        self.assertEqual(self.engine.scheduler.run_once(time.time() + 1)["status"], "succeeded")
        limited = self.engine.scheduler.run_once(time.time() + 1)
        self.assertEqual(limited["status"], "pending")
        self.assertIn("rate", self.store.get_webhook_delivery(second_job, "development")["status"])
        self.assertEqual(len(delivered), 1)
        self.assertEqual(self.store.get_webhook_delivery(first_job, "development")["status"], "delivered")

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

    def test_postgres_queue_schema_contains_distributed_coordination_contract(self):
        self.assertIn("lease_token VARCHAR(100)", POSTGRES_SCHEMA)
        constants = " ".join(str(item) for item in __import__("agentweb.rdbms", fromlist=["PostgresDistributedQueue"]).PostgresDistributedQueue.claim_due_job.__code__.co_consts)
        self.assertIn("FOR UPDATE SKIP LOCKED", constants)
        self.assertIn("CREATE TABLE IF NOT EXISTS queue_rate_limits", POSTGRES_SCHEMA)
        self.assertIn("CREATE TABLE IF NOT EXISTS metric_points", POSTGRES_SCHEMA)
        self.assertIn("idx_metric_points_org_time", POSTGRES_SCHEMA)

    def test_postgres_metric_store_aggregates_and_filters_by_organization(self):
        class FakeCursor:
            def __init__(self, rows):
                self.rows = rows
                self.selected_rows = rows
                self.statements = []
                self.rowcount = 3

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def execute(self, query, params=()):
                self.statements.append((query, params))
                if "WHERE org_id=%s" in query:
                    self.selected_rows = [row for row in self.rows if row[0] == params[0]]
                else:
                    self.selected_rows = self.rows

            def fetchall(self):
                return self.selected_rows

        class FakeConnection:
            def __init__(self, cursor):
                self.cursor_instance = cursor

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def cursor(self):
                return self.cursor_instance

        class FakeCoordinator:
            def __init__(self, connection):
                self.connection_instance = connection

            def connection(self):
                return self.connection_instance

        rows = [
            ("org-a", 'request_count|{"endpoint":"/solve","org_id":"org-a"}', "counter", 4, 0, 0, None),
            ("org-b", 'request_count|{"endpoint":"/solve","org_id":"org-b"}', "counter", 9, 0, 0, None),
            ("org-a", 'request_latency|{"endpoint":"/solve","org_id":"org-a"}', "observation", 0, 2, 1.5, None),
        ]
        cursor = FakeCursor(rows)
        store = PostgresMetricStore(FakeCoordinator(FakeConnection(cursor)))
        store.increment("request_count|{\"org_id\":\"org-a\"}", 1, {"org_id": "org-a"})
        store.observe("request_latency|{\"org_id\":\"org-a\"}", 0.75, {"org_id": "org-a"})
        store.gauge("queue_depth|{\"org_id\":\"org-a\"}", 2, {"org_id": "org-a"})
        visible = store.snapshot("org-a")
        self.assertEqual(visible["counters"]["request_count{endpoint=/solve,org_id=org-a}"], 4)
        self.assertNotIn("request_count{endpoint=/solve,org_id=org-b}", visible["counters"])
        self.assertEqual(visible["observations"]["request_latency{endpoint=/solve,org_id=org-a}"], {"count": 2, "sum": 1.5})
        self.assertEqual(store.purge_expired(60, now=time.time() + 61, org_id="org-a"), 3)
        self.assertEqual(len(cursor.statements), 5)
        self.assertTrue(all("metric_points" in statement[0] for statement in cursor.statements))
        self.assertIn("org_id=%s", cursor.statements[-1][0])
        self.assertIn("updated_at < %s", cursor.statements[-1][0])

    def test_engine_selects_postgres_metrics_only_for_distributed_coordinator(self):
        self.assertIsInstance(self.engine.metrics.store, MetricStore)
        distributed = object.__new__(PostgresDistributedQueue)
        distributed.connection = lambda: None
        engine = AgentWebEngine(self.store, queue_coordinator=distributed)
        self.assertIsInstance(engine.metrics.store, PostgresMetricStore)

    def test_distributed_queue_requires_postgresql_url(self):
        with patch.dict(os.environ, {"AGENTWEB_DISTRIBUTED_QUEUE": "1"}, clear=False):
            with self.assertRaises(DatabaseConfigurationError):
                open_distributed_queue(DatabaseConfig("development", "sqlite:///local.sqlite3"))

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
        thread = start_test_server(server)
        try:
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/health")) as response:
                self.assertEqual(response.status, 200)
                payload = json.loads(response.read())
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["service"], "agentweb")
            self.assertEqual(payload["checks"]["memory"], "ok")
            self.assertEqual(payload["checks"]["metrics"], "ok")
            self.assertEqual(payload["checks"]["audit"], "ok")
            self.assertEqual(payload["checks"]["queue"], "disabled")
        finally:
            stop_test_server(server, thread)

    def test_health_reports_degraded_metric_backend_without_details(self):
        server = create_server("127.0.0.1", 0, str(Path(self.temp_dir.name) / "health-degraded.sqlite3"))
        server.engine.metrics.health = lambda: False
        thread = start_test_server(server)
        try:
            with self.assertRaises(HTTPError) as raised:
                urlopen(Request(f"http://127.0.0.1:{server.server_port}/health"))
            self.assertEqual(raised.exception.code, 503)
            payload = json.loads(raised.exception.read())
            self.assertEqual(payload["status"], "degraded")
            self.assertEqual(payload["checks"]["metrics"], "failed")
            self.assertNotIn("sqlite", json.dumps(payload).lower())
            self.assertNotIn("password", json.dumps(payload).lower())
        finally:
            stop_test_server(server, thread)

    def test_http_crawl_route_returns_bounded_pages(self):
        server = create_server("127.0.0.1", 0, str(Path(self.temp_dir.name) / "crawl.sqlite3"))
        thread = start_test_server(server)
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
            stop_test_server(server, thread)

    def test_http_browser_credentials_are_metadata_only_and_revocable(self):
        original = FixtureHandler.body
        FixtureHandler.body = b"<html><body><form><input id='username'><input id='password' type='password'></form></body></html>"
        os.environ["AGENTWEB_CHROMIUM_PATH"] = "/usr/bin/chromium"
        os.environ["AGENTWEB_BROWSER_CREDENTIAL_KEY"] = Fernet.generate_key().decode()
        data_path = Path(self.temp_dir.name) / "browser-credentials-api.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        admin_a = server.authenticator.key_store.create_key("org-a", ["admin:*"])['secret']
        admin_b = server.authenticator.key_store.create_key("org-b", ["admin:*"])['secret']
        thread = start_test_server(server)
        try:
            headers = {"Authorization": f"Bearer {admin_a}", "Content-Type": "application/json"}
            body = json.dumps({"label": "fixture", "username": "alice@example.com", "secret": "password-123"}).encode()
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/admin/browser-credentials", data=body, method="POST", headers=headers)) as response:
                created = json.loads(response.read())
            self.assertNotIn("secret", created)
            self.assertNotIn("password-123", json.dumps(created))
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/admin/browser-credentials", headers={"Authorization": f"Bearer {admin_a}"})) as response:
                listing = json.loads(response.read())
            self.assertEqual(len(listing["data"]), 1)
            self.assertNotIn("password-123", json.dumps(listing))
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/admin/browser-credentials", headers={"Authorization": f"Bearer {admin_b}"})) as response:
                other_listing = json.loads(response.read())
            self.assertEqual(other_listing["data"], [])
            session_body = json.dumps({"url": self.url, "credential_id": created["id"], "actions": [{"type": "fill_credential", "selector": "#username", "field": "username"}, {"type": "fill_credential", "selector": "#password", "field": "secret"}]}).encode()
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/browser/sessions", data=session_body, method="POST", headers=headers)) as response:
                session = json.loads(response.read())
            self.assertNotIn("password-123", json.dumps(session))
            audit_request = Request(f"http://127.0.0.1:{server.server_port}/admin/audit?action=browser_credential.created", headers={"Authorization": f"Bearer {admin_a}"})
            with urlopen(audit_request) as response:
                audit = json.loads(response.read())
            self.assertNotIn("password-123", json.dumps(audit))
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/admin/browser-credentials/{created['id']}", method="DELETE", headers={"Authorization": f"Bearer {admin_a}", "Idempotency-Key": "revoke-credential-1"})) as response:
                self.assertEqual(response.status, 204)
            with self.assertRaises(HTTPError) as raised:
                urlopen(Request(f"http://127.0.0.1:{server.server_port}/admin/browser-credentials/{created['id']}", method="DELETE", headers={"Authorization": f"Bearer {admin_a}"}))
            self.assertEqual(raised.exception.code, 404)
        finally:
            FixtureHandler.body = original
            stop_test_server(server, thread)

    def test_http_browser_route_returns_rendered_session(self):
        os.environ["AGENTWEB_CHROMIUM_PATH"] = "/usr/bin/chromium"
        server = create_server("127.0.0.1", 0, str(Path(self.temp_dir.name) / "browser.sqlite3"))
        thread = start_test_server(server)
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
            stop_test_server(server, thread)

    def test_tenant_isolation_hides_monitor_and_trace_from_other_org(self):
        data_path = Path(self.temp_dir.name) / "tenants.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        admin_a = server.authenticator.key_store.create_key("org-a", ["admin:*"])["secret"]
        admin_b = server.authenticator.key_store.create_key("org-b", ["admin:*"])["secret"]
        thread = start_test_server(server)
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
            stop_test_server(server, thread)

    def test_http_audit_filters_pagination_and_time_validation(self):
        data_path = Path(self.temp_dir.name) / "audit-api.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        admin = server.authenticator.key_store.create_key("org-a", ["admin:*"])['secret']
        server.authenticator.key_store.audit("org-a", "operator", "config.changed", "monitor-1", {"version": 1})
        server.authenticator.key_store.audit("org-a", "operator", "config.changed", "monitor-2", {"version": 2})
        server.authenticator.key_store.audit("org-b", "operator", "config.changed", "monitor-3", {"version": 3})
        thread = start_test_server(server)
        try:
            headers = {"Authorization": f"Bearer {admin}"}
            base = f"http://127.0.0.1:{server.server_port}/admin/audit?action=config.changed&actor=operator&limit=1"
            with urlopen(Request(base, headers=headers)) as response:
                first = json.loads(response.read())
            self.assertEqual(len(first["data"]), 1)
            self.assertTrue(first["has_more"])
            self.assertEqual(first["data"][0]["org_id"], "org-a")
            self.assertEqual(first["data"][0]["target"], "monitor-2")
            with urlopen(Request(base + "&cursor=" + first["next_cursor"], headers=headers)) as response:
                second = json.loads(response.read())
            self.assertEqual(len(second["data"]), 1)
            self.assertEqual(second["data"][0]["target"], "monitor-1")
            with urlopen(Request(base + "&target=monitor-1&since=1970-01-01T00:00:00Z", headers=headers)) as response:
                filtered = json.loads(response.read())
            self.assertEqual([event["target"] for event in filtered["data"]], ["monitor-1"])
            for query in ("since=not-a-time", "since=10&until=1"):
                with self.assertRaises(HTTPError) as raised:
                    urlopen(Request(f"http://127.0.0.1:{server.server_port}/admin/audit?{query}", headers=headers))
                self.assertEqual(raised.exception.code, 400)
        finally:
            stop_test_server(server, thread)

    def test_persistent_keys_are_hashed_and_admin_listing_is_redacted(self):
        data_path = Path(self.temp_dir.name) / "keys.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        root = server.authenticator.key_store.create_key("org-a", ["admin:*"])["secret"]
        thread = start_test_server(server)
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
            stop_test_server(server, thread)

    def test_admin_revocation_is_organization_scoped_and_invalidates_key(self):
        data_path = Path(self.temp_dir.name) / "revoke.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        admin = server.authenticator.key_store.create_key("org-a", ["admin:*"])["secret"]
        other = server.authenticator.key_store.create_key("org-b", ["search:read"])
        thread = start_test_server(server)
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
            stop_test_server(server, thread)

    def test_http_idempotency_replays_and_conflicts(self):
        data_path = Path(self.temp_dir.name) / "idempotency.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        admin = server.authenticator.key_store.create_key("org-a", ["admin:*"])["secret"]
        thread = start_test_server(server)
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
            stop_test_server(server, thread)

    def test_http_rate_limit_headers_and_data_deletion(self):
        data_path = Path(self.temp_dir.name) / "headers.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        admin = server.authenticator.key_store.create_key("org-a", ["admin:*"])['secret']
        thread = start_test_server(server)
        try:
            headers = {"Authorization": f"Bearer {admin}", "Content-Type": "application/json"}
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/admin/usage", headers=headers)) as response:
                self.assertIn("X-RateLimit-Limit", response.headers)
                self.assertIn("X-RateLimit-Remaining", response.headers)
                self.assertIn("X-RateLimit-Reset", response.headers)
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/admin/metrics", headers=headers)) as response:
                metrics = json.loads(response.read())
            self.assertIn("counters", metrics)
            self.assertIn("observations", metrics)
            trace = server.engine.solve(f"Summarize {self.url}", org_id="org-a")
            server.engine.memory.snapshot(self.url, "content", "2026-08-24T00:00:00Z", "org-a")
            body = json.dumps({"kind": "all", "idempotency_key": "delete-1"}).encode()
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/admin/data", data=body, method="DELETE", headers=headers)) as response:
                deleted = json.loads(response.read())
            self.assertEqual(deleted["deleted_snapshots"], 2)
            self.assertEqual(deleted["deleted_traces"], 1)
            self.assertIsNone(server.engine.traces.get(trace.execution_id, "org-a"))
        finally:
            stop_test_server(server, thread)

    def test_http_admin_metrics_are_tenant_filtered(self):
        data_path = Path(self.temp_dir.name) / "metrics-api.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        admin_a = server.authenticator.key_store.create_key("org-a", ["admin:*"])['secret']
        server.authenticator.key_store.create_key("org-b", ["admin:*"])
        server.engine.metrics.increment("tenant_probe", labels={"org_id": "org-a"})
        server.engine.metrics.increment("tenant_probe", labels={"org_id": "org-b"})
        thread = start_test_server(server)
        try:
            request = Request(f"http://127.0.0.1:{server.server_port}/admin/metrics", headers={"Authorization": f"Bearer {admin_a}"})
            with urlopen(request) as response:
                metrics = json.loads(response.read())
            self.assertIn("counters", metrics)
            self.assertIn("observations", metrics)
            self.assertIn("gauges", metrics)
            self.assertIn("tenant_probe{org_id=org-a}", metrics["counters"])
            self.assertNotIn("tenant_probe{org_id=org-b}", metrics["counters"])
        finally:
            stop_test_server(server, thread)

    def test_http_usage_and_cursor_paginated_monitors(self):
        data_path = Path(self.temp_dir.name) / "usage.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        admin = server.authenticator.key_store.create_key("org-a", ["admin:*"])["secret"]
        thread = start_test_server(server)
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
            stop_test_server(server, thread)

    def test_http_monitor_change_policy_persists_and_validates(self):
        data_path = Path(self.temp_dir.name) / "monitor-policy.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        admin = server.authenticator.key_store.create_key("org-a", ["admin:*"])['secret']
        thread = start_test_server(server)
        try:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {admin}"}
            body = json.dumps({
                "task": f"Watch availability for {self.url}",
                "frequency": "daily",
                "change_policy": {"kind": "availability", "required_state": "in stock", "ignore_whitespace": True},
            }).encode()
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/observe", data=body, method="POST", headers=headers)) as response:
                created = json.loads(response.read())
            self.assertEqual(created["change_policy"]["kind"], "availability")
            self.assertTrue(created["change_policy"]["ignore_whitespace"])
            with urlopen(Request(f"http://127.0.0.1:{server.server_port}/observe/{created['id']}", headers=headers)) as response:
                fetched = json.loads(response.read())
            self.assertEqual(fetched["change_policy"]["required_state"], "in stock")

            for invalid_policy in ({"kind": "other"}, {"kind": "price", "absolute_delta": -1}, {"kind": "price", "relative_delta_percent": "5"}, {"kind": "availability", "required_state": "maybe"}):
                invalid_body = json.dumps({"task": f"Watch {self.url}", "frequency": "daily", "change_policy": invalid_policy}).encode()
                with self.assertRaises(HTTPError) as raised:
                    urlopen(Request(f"http://127.0.0.1:{server.server_port}/observe", data=invalid_body, method="POST", headers=headers))
                self.assertEqual(raised.exception.code, 400)
        finally:
            stop_test_server(server, thread)

    def test_http_error_boundary_redacts_credential_bearing_urls(self):
        data_path = Path(self.temp_dir.name) / "error-redaction.sqlite3"
        server = create_server("127.0.0.1", 0, str(data_path))
        key = server.authenticator.key_store.create_key("org-a", ["extract:read"])['secret']
        thread = start_test_server(server)
        try:
            body = json.dumps({"url": "https://user:secret@example.test/path"}).encode()
            request = Request(f"http://127.0.0.1:{server.server_port}/extract", data=body, method="POST", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            with self.assertRaises(HTTPError) as raised:
                urlopen(request)
            self.assertNotIn("secret", raised.exception.read().decode())
        finally:
            stop_test_server(server, thread)

    def test_browser_worker_pool_rejects_capacity_overflow(self):
        browser = BrowserEngine(max_workers=1, session_timeout=0.01)
        with browser._worker_slot():
            with self.assertRaises(BrowserUnavailableError):
                with browser._worker_slot():
                    pass

    def test_http_scope_auth_rejects_missing_scope(self):
        os.environ["AGENTWEB_API_KEYS"] = json.dumps({"search-only": ["search:read"]})
        server = create_server("127.0.0.1", 0, str(Path(self.temp_dir.name) / "auth.sqlite3"))
        thread = start_test_server(server)
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
            stop_test_server(server, thread)


if __name__ == "__main__":
    unittest.main()
