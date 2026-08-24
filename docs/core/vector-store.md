# Vector store

AgentWeb includes a dependency-free `VectorStore` for two bounded similarity use cases: semantic fallback matching for registered skills and cautious entity resolution during graph ingestion. Embeddings are deterministic hashed-token vectors, so local runs are reproducible and do not require a hosted model or external service.

## Interface

```python
from agentweb import VectorStore

vectors = VectorStore("agentweb.sqlite3")
query = vectors.embed("software release announcements")
vectors.upsert("skills", "release_watch", "Track software announcements", {"name": "release_watch"})
results = vectors.nearest(query, k=5, namespace="skills")
```

Namespaces are isolated. The runtime uses `skills` for skill descriptions and `entities:<org_id>` for tenant-scoped graph entities; vectors from one namespace cannot be returned by another. Persisted metadata is bounded and contains identifiers and descriptors, not page bodies or credentials.

The skill registry first applies its existing keyword and description scoring, then uses a conservative vector threshold when lexical evidence is insufficient. Graph entity upserts first apply exact `(organization, type, case-insensitive name)` matching and then use a high-similarity, same-type vector candidate before creating a new node. This avoids merging unrelated entities while handling common name variants such as an abbreviated company name and its corporate suffix.
