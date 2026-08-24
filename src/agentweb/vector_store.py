"""Deterministic local vector storage for skills and entity resolution."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


@dataclass(frozen=True)
class Match:
    item_id: str
    score: float
    metadata: dict[str, Any]


Vector = tuple[float, ...]


class VectorStore:
    """Small deterministic vector backend with separate namespaces."""

    dimension = 64

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else None
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS vectors (namespace TEXT NOT NULL, item_id TEXT NOT NULL, vector_json TEXT NOT NULL, metadata_json TEXT NOT NULL, PRIMARY KEY(namespace, item_id))"
                )

    def _connect(self) -> sqlite3.Connection:
        if self.path is None:
            raise RuntimeError("in-memory vector store has no database connection")
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @classmethod
    def embed(cls, text: str) -> Vector:
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        tokens = _TOKEN_RE.findall(text.lower())
        vector = [0.0] * cls.dimension
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            for offset in range(0, len(digest), 2):
                bucket = int.from_bytes(digest[offset : offset + 2], "big") % cls.dimension
                sign = 1.0 if digest[offset] & 1 else -1.0
                vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return tuple(vector)
        return tuple(round(value / norm, 8) for value in vector)

    @classmethod
    def _cosine(cls, left: Vector, right: Vector) -> float:
        if len(left) != len(right) or not left:
            return 0.0
        return sum(a * b for a, b in zip(left, right))

    def upsert(self, namespace: str, item_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        namespace = str(namespace or "").strip()
        item_id = str(item_id or "").strip()
        if not namespace or len(namespace) > 80:
            raise ValueError("namespace must contain between 1 and 80 characters")
        if not item_id or len(item_id) > 200:
            raise ValueError("item_id must contain between 1 and 200 characters")
        payload = metadata or {}
        if not isinstance(payload, dict):
            raise ValueError("metadata must be an object")
        vector = self.embed(text)
        if self.path is None:
            if not hasattr(self, "_memory"):
                self._memory: dict[tuple[str, str], tuple[Vector, dict[str, Any]]] = {}
            self._memory[(namespace, item_id)] = (vector, payload)
            return
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO vectors(namespace, item_id, vector_json, metadata_json) VALUES (?, ?, ?, ?) ON CONFLICT(namespace, item_id) DO UPDATE SET vector_json=excluded.vector_json, metadata_json=excluded.metadata_json",
                (namespace, item_id, json.dumps(vector), json.dumps(payload, sort_keys=True)),
            )

    def nearest(self, vector: Vector, k: int = 10, namespace: str = "") -> list[Match]:
        if not isinstance(vector, tuple):
            vector = tuple(float(value) for value in vector)
        if len(vector) != self.dimension:
            raise ValueError(f"vector must have dimension {self.dimension}")
        bounded_k = max(1, min(int(k), 100))
        rows: list[tuple[str, Vector, dict[str, Any]]] = []
        if self.path is None:
            for (stored_namespace, item_id), (stored_vector, metadata) in getattr(self, "_memory", {}).items():
                if not namespace or stored_namespace == namespace:
                    rows.append((item_id, stored_vector, metadata))
        else:
            with self._connect() as connection:
                stored = connection.execute(
                    "SELECT item_id, vector_json, metadata_json FROM vectors WHERE namespace=? ORDER BY item_id LIMIT 1000",
                    (namespace,),
                ).fetchall()
            rows = [(row["item_id"], tuple(json.loads(row["vector_json"])), json.loads(row["metadata_json"])) for row in stored]
        matches = [Match(item_id, round(max(-1.0, min(1.0, self._cosine(vector, stored_vector))), 6), metadata) for item_id, stored_vector, metadata in rows]
        matches.sort(key=lambda item: (-item.score, item.item_id))
        return matches[:bounded_k]

    def health(self) -> bool:
        if self.path is None:
            return True
        try:
            with self._connect() as connection:
                return connection.execute("SELECT 1").fetchone()[0] == 1
        except (OSError, sqlite3.Error):
            return False
