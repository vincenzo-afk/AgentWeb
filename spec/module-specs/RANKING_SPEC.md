# Ranking Spec

## Purpose
Score sources/evidence for reliability and relevance. See [docs/core/ranking.md](../../docs/core/ranking.md) and [docs/concepts/trust-model.md](../../docs/concepts/trust-model.md).

## Interface
```
rank(sources: Source[], task_context: TaskContext) -> RankedSource[]
```

## Signal inputs
Source reputation, cross-source corroboration, recency, content-type appropriateness, extraction confidence (from [EXTRACTOR_SPEC.md](EXTRACTOR_SPEC.md)).

## Output
Each source gets a `trust_score` (0-1) and inclusion recommendation for [SYNTHESIS_SPEC.md](SYNTHESIS_SPEC.md). Domain-specific overrides supported (see [docs/guides/custom-rankers.md](../../docs/guides/custom-rankers.md)).

## Relationship to Trust Engine
Ranking scores *relevance/reliability* for ordering; [TRUST_ENGINE_SPEC.md](TRUST_ENGINE_SPEC.md) gates *whether a source should be touched/used at all*.
