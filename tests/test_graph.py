from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agentweb.api import create_server
from agentweb.engine import AgentWebEngine
from agentweb.graph import GraphStore
from agentweb.memory import MemoryStore
from agentweb.scheduler import Scheduler
from agentweb.models import Monitor
from agentweb.workflows import WorkflowStore


class GraphStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = GraphStore(Path(self.temp_dir.name) / "graph.sqlite3")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_upserts_merge_sources_and_query_confidence(self) -> None:
        acme = self.store.upsert_entity({"type": "Company", "name": "Acme", "confidence": 0.7, "source_id": "src_a"}, "org_a")
        product = self.store.upsert_entity({"type": "Product", "name": "Widget", "confidence": 0.8, "source_ids": ["src_a", "src_b"]}, "org_a")
        first = self.store.upsert_relation(acme.id, product.id, "produces", 0.6, "org_a", "src_a")
        second = self.store.upsert_relation(acme.id, product.id, "produces", 0.65, "org_a", "src_b")

        self.assertEqual(first.id, second.id)
        self.assertEqual(second.observations, 2)
        result = self.store.query(entity_type="Company", relation="produces", org_id="org_a")
        self.assertEqual([node.name for node in result.nodes], ["Acme", "Widget"])
        self.assertEqual(len(result.edges), 1)
        self.assertEqual(result.edges[0].source_ids, ["src_a", "src_b"])
        self.assertGreater(result.edges[0].confidence, 0.65)

    def test_queries_are_tenant_scoped_and_support_related_to(self) -> None:
        left = self.store.upsert_entity({"type": "Person", "name": "Ada"}, "org_a")
        right = self.store.upsert_entity({"type": "Project", "name": "Graph"}, "org_a")
        other = self.store.upsert_entity({"type": "Project", "name": "Graph"}, "org_b")
        self.store.upsert_relation(left.id, right.id, "works_on", 0.9, "org_a")
        result = self.store.query(related_to=right.id, org_id="org_a")
        self.assertEqual(len(result.edges), 1)
        self.assertEqual({node.id for node in result.nodes}, {left.id, right.id})
        self.assertEqual(self.store.query(related_to=other.id, org_id="org_a").edges, [])

    def test_bounded_multihop_query_resolves_anchor_name(self) -> None:
        ada = self.store.upsert_entity({"type": "Person", "name": "Ada"}, "org_a")
        project = self.store.upsert_entity({"type": "Project", "name": "Graph"}, "org_a")
        repo = self.store.upsert_entity({"type": "Repository", "name": "AgentWeb"}, "org_a")
        self.store.upsert_relation(ada.id, project.id, "works_on", 0.9, "org_a")
        self.store.upsert_relation(project.id, repo.id, "contains", 0.85, "org_a")
        result = self.store.query(related_to="Ada", org_id="org_a", depth=2)
        self.assertEqual({edge.relation for edge in result.edges}, {"works_on", "contains"})
        self.assertEqual({node.name for node in result.nodes}, {"Ada", "Graph", "AgentWeb"})

    def test_document_ingestion_creates_provenance_edges(self) -> None:
        counts = self.store.ingest_document("https://example.com/page", "Example Page", ["Acme", "Widget", "Acme"], "src_page", "org_a", 0.8)
        self.assertEqual(counts, {"pages": 1, "entities": 2, "relations": 2})
        result = self.store.query(entity_type="Page", related_to="Example Page", org_id="org_a")
        self.assertEqual(len(result.edges), 2)
        self.assertEqual({node.type for node in result.nodes}, {"Page", "Mention"})
        self.assertTrue(all("src_page" in node.source_ids for node in result.nodes))

    def test_solve_can_use_graph_context_as_grounded_sources(self) -> None:
        ada = self.store.upsert_entity({"type": "Person", "name": "Ada", "attributes": {"role": "founder"}}, "development")
        project = self.store.upsert_entity({"type": "Project", "name": "Graph"}, "development")
        self.store.upsert_relation(ada.id, project.id, "works_on", 0.9, "development", "src_profile")
        response = AgentWebEngine(MemoryStore(self.store.path)).solve(
            "Which project does Ada work on?",
            org_id="development",
            inputs={"graph_query": {"related_to": "Ada", "depth": 1}},
        )
        self.assertTrue(any(source.url.startswith("graph://") for source in response.sources))
        self.assertTrue(any(action.get("tool") == "graph" for action in response.actions))
        self.assertIn("graph_context", response.selection_logic["source_strategy"])


class WorkflowStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        path = Path(self.temp_dir.name) / "workflow.sqlite3"
        self.memory = MemoryStore(path)
        self.executions: list[tuple[str, str, str]] = []

        def execute(task: str, mode: str, org_id: str):
            self.executions.append((task, mode, org_id))
            return {"execution_id": "exec_workflow"}

        self.store = WorkflowStore(path, execute)
        self.monitor = Monitor(id="mon_workflow", task="Watch https://example.com", org_id="org_a", target_url="https://example.com")
        self.memory.create_monitor(self.monitor)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_change_event_renders_template_and_persists_run(self) -> None:
        workflow = self.store.create("Summarize changes", self.monitor.id, "Summarize {target} from {to_hash}", org_id="org_a")
        runs = self.store.trigger_for_monitor(self.monitor.id, "org_a", "monitor.change_detected", {"target": "https://example.com", "to_hash": "hash_new"})
        self.assertEqual(workflow["event"], "monitor.change_detected")
        self.assertEqual(self.executions, [("Summarize https://example.com from hash_new", "focus", "org_a")])
        self.assertEqual(runs[0]["status"], "succeeded")
        self.assertEqual(runs[0]["execution_id"], "exec_workflow")
        self.assertEqual(self.store.list_runs("org_b"), [])

    def test_trigger_queues_and_scheduler_executes_run(self) -> None:
        queued = WorkflowStore(self.memory.path, self.store.executor, self.memory.enqueue_workflow_run)
        queued.create("Queued summary", self.monitor.id, "Summarize {target}", org_id="org_a")
        runs = queued.trigger_for_monitor(self.monitor.id, "org_a", "monitor.change_detected", {"target": "https://example.com"})
        self.assertEqual(runs[0]["status"], "queued")
        scheduler = Scheduler(self.memory, lambda monitor: monitor, workflow_runner=queued.execute_queued_run)
        result = None
        for _ in range(3):
            result = scheduler.run_once(now=time.time() + 1)
            if result and result.get("result", {}).get("run_id"):
                break
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(queued.list_runs("org_a")[0]["status"], "succeeded")
        self.assertEqual(self.executions[-1][0], "Summarize https://example.com")

    def test_workflow_can_be_paused_and_resumed(self) -> None:
        workflow = self.store.create("Controlled", self.monitor.id, "Summarize {target}", org_id="org_a")
        paused = self.store.set_status(workflow["id"], "paused", "org_a")
        self.assertEqual(paused["status"], "paused")
        resumed = self.store.set_status(workflow["id"], "active", "org_a")
        self.assertEqual(resumed["status"], "active")
        self.assertEqual(self.store.list("org_b"), [])

    def test_template_errors_are_recorded_without_raising(self) -> None:
        self.store.create("Broken", self.monitor.id, "Use {missing}", org_id="org_a")
        runs = self.store.trigger_for_monitor(self.monitor.id, "org_a", "monitor.change_detected", {})
        self.assertEqual(runs[0]["status"], "failed")
        self.assertIn("missing", runs[0]["error"])
        self.assertEqual(self.executions, [])


class GraphApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.server = create_server("127.0.0.1", 0, str(Path(self.temp_dir.name) / "api.sqlite3"))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()
        self.temp_dir.cleanup()

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, dict, dict[str, str]]:
        body = None if payload is None else json.dumps(payload).encode()
        request = Request(self.base_url + path, data=body, method=method, headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read()), dict(response.headers)
        except HTTPError as error:
            return error.code, json.loads(error.read()), dict(error.headers)

    def test_canonical_graph_routes_and_metadata(self) -> None:
        status, acme, headers = self.request("POST", "/v1/graph/entities", {"type": "Company", "name": "Acme"})
        self.assertEqual(status, 201)
        self.assertEqual(acme["type"], "Company")
        self.assertEqual(acme["_meta"]["api_version"], "v1")
        status, product, _ = self.request("POST", "/v1/graph/entities", {"type": "Product", "name": "Widget"})
        self.assertEqual(status, 201)
        status, relation, _ = self.request(
            "POST",
            "/v1/graph/relations",
            {"from_id": acme["id"], "to_id": product["id"], "relation": "produces", "confidence": 0.8},
        )
        self.assertEqual(status, 201)
        self.assertEqual(relation["relation"], "produces")
        status, result, headers = self.request("GET", "/v1/graph/query?entity_type=Company&relation=produces")
        self.assertEqual(status, 200)
        self.assertEqual(len(result["edges"]), 1)
        self.assertEqual(len(result["nodes"]), 2)
        self.assertEqual(result["_meta"]["path"], "/v1/graph/query")
        self.assertIn("X-AgentWeb-API-Version", headers)

    def test_invalid_graph_relation_is_a_client_error(self) -> None:
        status, payload, _ = self.request("POST", "/v1/graph/relations", {"from_id": "ent_missing", "to_id": "ent_other", "relation": "links"})
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["type"], "invalid_request")

    def test_graph_query_supports_cursor_pagination(self) -> None:
        entities = []
        for name in ("A", "B", "C", "D"):
            status, entity, _ = self.request("POST", "/v1/graph/entities", {"type": "Node", "name": name})
            self.assertEqual(status, 201)
            entities.append(entity["id"])
        for left, right in zip(entities, entities[1:]):
            status, _, _ = self.request("POST", "/v1/graph/relations", {"from_id": left, "to_id": right, "relation": "links"})
            self.assertEqual(status, 201)
        status, first, _ = self.request("GET", "/v1/graph/query?limit=1")
        self.assertEqual(status, 200)
        self.assertTrue(first["has_more"])
        self.assertIsNotNone(first["next_cursor"])
        status, second, _ = self.request("GET", "/v1/graph/query?limit=1&cursor=" + first["next_cursor"])
        self.assertEqual(status, 200)
        self.assertNotEqual(first["edges"][0]["id"], second["edges"][0]["id"])

    def test_graph_query_paginates_isolated_entities(self) -> None:
        for name in ("Orphan A", "Orphan B", "Orphan C"):
            status, _, _ = self.request("POST", "/v1/graph/entities", {"type": "Orphan", "name": name})
            self.assertEqual(status, 201)
        status, first, _ = self.request("GET", "/v1/graph/query?entity_type=Orphan&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(len(first["nodes"]), 1)
        self.assertTrue(first["has_more"])
        status, second, _ = self.request("GET", "/v1/graph/query?entity_type=Orphan&limit=1&cursor=" + first["next_cursor"])
        self.assertEqual(status, 200)
        self.assertEqual(len(second["nodes"]), 1)
        self.assertNotEqual(first["nodes"][0]["id"], second["nodes"][0]["id"])

    def test_graph_depth_is_bounded(self) -> None:
        status, payload, _ = self.request("GET", "/v1/graph/query?depth=4")
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["type"], "invalid_request")

    def test_solve_accepts_top_level_graph_query(self) -> None:
        status, entity, _ = self.request("POST", "/v1/graph/entities", {"type": "Company", "name": "Acme"})
        self.assertEqual(status, 201)
        status, response, _ = self.request(
            "POST",
            "/v1/solve",
            {"task": "Summarize Acme", "graph_query": {"related_to": "Acme", "depth": 1}},
        )
        self.assertEqual(status, 200)
        self.assertTrue(any(action.get("tool") == "graph" for action in response["actions"]))
        self.assertTrue(any(source["url"].startswith("graph://") for source in response["sources"]))
        self.assertEqual(entity["name"], "Acme")

    def test_workflow_routes_are_tenant_scoped_and_validated(self) -> None:
        status, payload, _ = self.request("GET", "/v1/workflows")
        self.assertEqual(status, 200)
        self.assertEqual(payload["workflows"], [])
        self.assertEqual(payload["_meta"]["path"], "/v1/workflows")
        status, payload, _ = self.request("POST", "/v1/workflows", {"name": "Missing monitor", "monitor_id": "mon_missing", "task_template": "Summarize {target}"})
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["type"], "invalid_request")


if __name__ == "__main__":
    unittest.main()
