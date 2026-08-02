# Memory Spec

## Purpose
Snapshot, hash, compare, and reuse prior page/content state. See [docs/core/memory.md](../../docs/core/memory.md) and [docs/concepts/memory-model.md](../../docs/concepts/memory-model.md).

## Interface
```
snapshot(target: string, content: NormalizedContent) -> Snapshot
diff(target: string, from_hash: string, to_hash: string) -> Diff
get_latest(target: string) -> Snapshot | null
```

## Storage model
Content-addressed by hash; see [../data/STORAGE_SPEC.md](../data/STORAGE_SPEC.md) and [../data/OBJECT_MODEL.md](../data/OBJECT_MODEL.md) for the `Snapshot` schema.

## Reuse policy
A snapshot is considered "fresh enough" to reuse if it's within the task's implied recency tolerance (e.g., pricing tasks tolerate shorter freshness windows than historical-fact tasks). Reuse policy parameters are configurable per [../config/FEATURE_FLAGS.md](../config/FEATURE_FLAGS.md).

## Retention
See [../../docs/operations/data-retention.md](../../docs/operations/data-retention.md).
