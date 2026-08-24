"""Tenant-scoped knowledge graph storage and deterministic query helpers."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _confidence(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("confidence must be a number between 0 and 1") from error
    if not 0.0 <= parsed <= 1.0:
        raise ValueError("confidence must be a number between 0 and 1")
    return round(parsed, 4)


def _source_ids(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        raise ValueError("source_ids must be a string or an array of strings")
    result: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("source_ids must contain non-empty strings")
        if value not in result:
            result.append(value)
    return result[:50]


def _json_object(value: Any, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


@dataclass(frozen=True)
class Entity:
    id: str
    org_id: str
    type: str
    name: str
    attributes: dict[str, Any]
    confidence: float
    source_ids: list[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "type": self.type,
            "name": self.name,
            "attributes": self.attributes,
            "confidence": self.confidence,
            "source_ids": self.source_ids,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class Relation:
    id: str
    org_id: str
    from_id: str
    to_id: str
    relation: str
    confidence: float
    source_ids: list[str]
    observations: int
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "from": self.from_id,
            "to": self.to_id,
            "relation": self.relation,
            "confidence": self.confidence,
            "source_ids": self.source_ids,
            "observations": self.observations,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class GraphResult:
    nodes: list[Entity]
    edges: list[Relation]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }


class GraphStore:
    """Small local-first graph store sharing the application's SQLite file."""

    def __init__(self, path: str | Path = "agentweb.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS graph_entities (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    name_normalized TEXT NOT NULL,
                    attributes_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(org_id, entity_type, name_normalized)
                );
                CREATE INDEX IF NOT EXISTS idx_graph_entities_org_type
                    ON graph_entities(org_id, entity_type, name_normalized);
                CREATE TABLE IF NOT EXISTS graph_relations (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    from_id TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source_ids_json TEXT NOT NULL,
                    observations INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(org_id, from_id, to_id, relation)
                );
                CREATE INDEX IF NOT EXISTS idx_graph_relations_org_from
                    ON graph_relations(org_id, from_id, relation);
                CREATE INDEX IF NOT EXISTS idx_graph_relations_org_to
                    ON graph_relations(org_id, to_id, relation);
                """
            )

    @staticmethod
    def _entity(row: sqlite3.Row) -> Entity:
        return Entity(
            id=row["id"],
            org_id=row["org_id"],
            type=row["entity_type"],
            name=row["name"],
            attributes=json.loads(row["attributes_json"]),
            confidence=float(row["confidence"]),
            source_ids=json.loads(row["source_ids_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _relation(row: sqlite3.Row) -> Relation:
        return Relation(
            id=row["id"],
            org_id=row["org_id"],
            from_id=row["from_id"],
            to_id=row["to_id"],
            relation=row["relation"],
            confidence=float(row["confidence"]),
            source_ids=json.loads(row["source_ids_json"]),
            observations=int(row["observations"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def upsert_entity(
        self,
        entity: dict[str, Any],
        org_id: str = "development",
    ) -> Entity:
        if not isinstance(entity, dict):
            raise ValueError("entity must be an object")
        entity_type = entity.get("type", entity.get("entity_type"))
        name = entity.get("name")
        if not isinstance(entity_type, str) or not entity_type.strip():
            raise ValueError("entity type must be a non-empty string")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("entity name must be a non-empty string")
        entity_type = entity_type.strip()[:120]
        name = name.strip()[:500]
        attributes = _json_object(entity.get("attributes"), "attributes")
        confidence = _confidence(entity.get("confidence", 0.5))
        sources = _source_ids(entity.get("source_ids", entity.get("source_id")))
        requested_id = entity.get("id")
        entity_id = requested_id.strip() if isinstance(requested_id, str) and requested_id.strip() else (
            "ent_" + uuid.uuid5(uuid.NAMESPACE_URL, f"{org_id}:{entity_type.lower()}:{name.casefold()}").hex[:20]
        )
        if not entity_id.startswith("ent_"):
            raise ValueError("entity id must start with ent_")
        now = _now()
        normalized = name.casefold()
        with self._connect() as connection:
            owner = connection.execute("SELECT org_id FROM graph_entities WHERE id=?", (entity_id,)).fetchone()
            if owner is not None and owner["org_id"] != org_id:
                raise ValueError("entity id is owned by another organization")
            row = connection.execute(
                "SELECT * FROM graph_entities WHERE org_id=? AND entity_type=? AND name_normalized=?",
                (org_id, entity_type, normalized),
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO graph_entities (id, org_id, entity_type, name, name_normalized, attributes_json, confidence, source_ids_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (entity_id, org_id, entity_type, name, normalized, json.dumps(attributes, sort_keys=True), confidence, json.dumps(sources), now, now),
                )
            else:
                entity_id = row["id"]
                merged_sources = list(dict.fromkeys(json.loads(row["source_ids_json"]) + sources))[:50]
                merged_attributes = json.loads(row["attributes_json"])
                merged_attributes.update(attributes)
                connection.execute(
                    "UPDATE graph_entities SET attributes_json=?, confidence=?, source_ids_json=?, updated_at=? WHERE id=? AND org_id=?",
                    (json.dumps(merged_attributes, sort_keys=True), max(float(row["confidence"]), confidence), json.dumps(merged_sources), now, entity_id, org_id),
                )
            result = connection.execute("SELECT * FROM graph_entities WHERE id=? AND org_id=?", (entity_id, org_id)).fetchone()
            if result is None:
                raise RuntimeError("entity upsert failed")
            return self._entity(result)

    def upsert_relation(
        self,
        from_id: str,
        to_id: str,
        relation: str,
        confidence: float = 0.5,
        org_id: str = "development",
        source_ids: Any = None,
    ) -> Relation:
        if not isinstance(from_id, str) or not from_id.strip() or not isinstance(to_id, str) or not to_id.strip():
            raise ValueError("from_id and to_id must be non-empty strings")
        if not isinstance(relation, str) or not relation.strip():
            raise ValueError("relation must be a non-empty string")
        confidence = _confidence(confidence)
        sources = _source_ids(source_ids)
        relation = relation.strip()[:120]
        now = _now()
        relation_id = "rel_" + uuid.uuid5(uuid.NAMESPACE_URL, f"{org_id}:{from_id}:{to_id}:{relation.casefold()}").hex[:20]
        with self._connect() as connection:
            entities = connection.execute(
                "SELECT id FROM graph_entities WHERE org_id=? AND id IN (?, ?)", (org_id, from_id.strip(), to_id.strip())
            ).fetchall()
            if len(entities) != 2:
                raise ValueError("both relation endpoints must belong to the organization")
            row = connection.execute(
                "SELECT * FROM graph_relations WHERE org_id=? AND from_id=? AND to_id=? AND relation=?",
                (org_id, from_id.strip(), to_id.strip(), relation),
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO graph_relations (id, org_id, from_id, to_id, relation, confidence, source_ids_json, observations, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (relation_id, org_id, from_id.strip(), to_id.strip(), relation, confidence, json.dumps(sources), 1, now, now),
                )
            else:
                merged_sources = list(dict.fromkeys(json.loads(row["source_ids_json"]) + sources))[:50]
                connection.execute(
                    "UPDATE graph_relations SET confidence=?, source_ids_json=?, observations=?, updated_at=? WHERE id=? AND org_id=?",
                    (max(float(row["confidence"]), confidence), json.dumps(merged_sources), int(row["observations"]) + 1, now, row["id"], org_id),
                )
                relation_id = row["id"]
            result = connection.execute("SELECT * FROM graph_relations WHERE id=? AND org_id=?", (relation_id, org_id)).fetchone()
            if result is None:
                raise RuntimeError("relation upsert failed")
            return self._relation(result)

    @staticmethod
    def _query_confidence(row: sqlite3.Row) -> float:
        base = float(row["confidence"])
        source_bonus = min(0.25, max(0, len(json.loads(row["source_ids_json"])) - 1) * 0.05)
        age_days = max(0.0, (datetime.now(timezone.utc) - datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))).total_seconds() / 86400)
        recency_factor = max(0.8, 1.0 - min(age_days, 365.0) / 365.0 * 0.2)
        return round(min(0.99, (base + source_bonus) * recency_factor), 4)

    def query(
        self,
        entity_type: str | None = None,
        related_to: str | None = None,
        relation: str | None = None,
        org_id: str = "development",
        limit: int = 100,
    ) -> GraphResult:
        bounded_limit = max(1, min(int(limit), 100))
        clauses = ["r.org_id=?"]
        params: list[Any] = [org_id]
        if related_to:
            clauses.append("(r.from_id=? OR r.to_id=?)")
            params.extend([related_to, related_to])
        if relation:
            clauses.append("r.relation=?")
            params.append(relation)
        if entity_type:
            clauses.append("(from_node.entity_type=? OR to_node.entity_type=?)")
            params.extend([entity_type, entity_type])
        with self._connect() as connection:
            edge_rows = connection.execute(
                "SELECT r.*, from_node.entity_type AS from_type, from_node.name AS from_name, to_node.entity_type AS to_type, to_node.name AS to_name "
                "FROM graph_relations r JOIN graph_entities from_node ON from_node.id=r.from_id AND from_node.org_id=r.org_id "
                "JOIN graph_entities to_node ON to_node.id=r.to_id AND to_node.org_id=r.org_id WHERE " + " AND ".join(clauses) + " ORDER BY r.updated_at DESC, r.id LIMIT ?",
                (*params, bounded_limit),
            ).fetchall()
            entity_ids = {row["from_id"] for row in edge_rows} | {row["to_id"] for row in edge_rows}
            entity_clauses = ["org_id=?"]
            entity_params: list[Any] = [org_id]
            if entity_type and not entity_ids:
                entity_clauses.append("entity_type=?")
                entity_params.append(entity_type)
            if related_to and not entity_ids:
                entity_clauses.append("id=?")
                entity_params.append(related_to)
            if entity_ids:
                placeholders = ",".join("?" for _ in entity_ids)
                entity_clauses.append(f"id IN ({placeholders})")
                entity_params.extend(sorted(entity_ids))
            entity_rows = connection.execute(
                "SELECT * FROM graph_entities WHERE " + " AND ".join(entity_clauses) + " ORDER BY name COLLATE NOCASE, id LIMIT ?",
                (*entity_params, bounded_limit),
            ).fetchall()
        edges = []
        for row in edge_rows:
            relation_item = self._relation(row)
            edges.append(Relation(**{**relation_item.__dict__, "confidence": self._query_confidence(row)}))
        return GraphResult(nodes=[self._entity(row) for row in entity_rows], edges=edges)

    def health(self) -> bool:
        try:
            with self._connect() as connection:
                return connection.execute("SELECT 1").fetchone()[0] == 1
        except (OSError, sqlite3.Error):
            return False
