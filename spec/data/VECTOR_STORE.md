# Vector Store

## Purpose
Embedding-based similarity search, used in two places:

1. **Skill matching** — embedding a task description and comparing against registered [Skill](../module-specs/SKILLS_SPEC.md) descriptions to find the best template match, rather than relying solely on keyword matching.
2. **Entity resolution** — comparing candidate entity names/descriptions during [Graph](../module-specs/GRAPH_SPEC.md) updates to determine whether a newly extracted entity is the same as an existing one (e.g., "Company X Inc." vs. "Company X") before creating a duplicate node.

## Interface
```
embed(text: string) -> Vector
nearest(vector: Vector, k: int, namespace: string) -> Match[]
```

## Namespaces
Separate vector namespaces for `skills` and `entities` so similarity search doesn't cross-contaminate between the two use cases.
