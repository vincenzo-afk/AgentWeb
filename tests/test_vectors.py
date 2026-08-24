from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentweb.skills import Skill, SkillRegistry
from agentweb.vector_store import VectorStore


class VectorStoreTests(unittest.TestCase):
    def test_embeddings_are_deterministic_and_nearest_is_ranked(self) -> None:
        store = VectorStore()
        vector = store.embed("Company X release")
        self.assertEqual(vector, store.embed("Company X release"))
        store.upsert("entities", "one", "Company X release", {"type": "Company"})
        store.upsert("entities", "two", "Unrelated cooking recipe", {"type": "Topic"})
        matches = store.nearest(vector, k=2, namespace="entities")
        self.assertEqual(matches[0].item_id, "one")
        self.assertGreater(matches[0].score, matches[1].score)
        self.assertEqual(store.nearest(vector, namespace="skills"), [])

    def test_entity_resolution_merges_similar_names_by_type(self) -> None:
        from agentweb.graph import GraphStore
        with tempfile.TemporaryDirectory() as directory:
            graph = GraphStore(Path(directory) / "graph.sqlite3")
            first = graph.upsert_entity({"type": "Company", "name": "Company X"}, "org_a")
            merged = graph.upsert_entity({"type": "Company", "name": "Company X Inc", "attributes": {"source": "filing"}}, "org_a")
            distinct = graph.upsert_entity({"type": "Company", "name": "Company Y"}, "org_a")
            self.assertEqual(first.id, merged.id)
            self.assertEqual(merged.attributes["source"], "filing")
            self.assertNotEqual(first.id, distinct.id)

    def test_persistent_store_round_trips_vectors_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vectors.sqlite3"
            first = VectorStore(path)
            first.upsert("skills", "summary", "summarize a source", {"name": "summary"})
            second = VectorStore(path)
            matches = second.nearest(second.embed("summarize a source"), namespace="skills")
            self.assertEqual(matches[0].item_id, "summary")
            self.assertEqual(matches[0].metadata["name"], "summary")

    def test_skill_registry_uses_vector_fallback_for_semantic_match(self) -> None:
        skill = Skill(
            name="release_watch",
            description="Track software announcements and version changes.",
            input_schema={},
            plan_template=(),
        )
        registry = SkillRegistry([skill])
        self.assertEqual(registry.match("track software announcements"), skill)


if __name__ == "__main__":
    unittest.main()
