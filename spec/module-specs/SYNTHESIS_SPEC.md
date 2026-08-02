# Synthesis Spec

## Purpose
Produce the final grounded, cited output. See [docs/core/synthesis.md](../../docs/core/synthesis.md) and [docs/api/citations.md](../../docs/api/citations.md).

## Interface
```
synthesize(ranked_sources: RankedSource[], task: string, output_format?: string) -> SynthesisResult
```

## Output guarantee
Every claim must map to at least one cited source via a `claim_span → source_ids` mapping. See [../api/RESPONSE_SCHEMA.md](../api/RESPONSE_SCHEMA.md).

## Handling conflicting evidence
When sources disagree, synthesis surfaces the disagreement explicitly (e.g., "Source A reports X; Source B reports Y") rather than silently picking one, per [docs/concepts/trust-model.md](../../docs/concepts/trust-model.md).

## Handling insufficient evidence
If ranked sources don't meet a minimum confidence/coverage threshold for the task, return a partial answer with an explicit `insufficient_evidence` flag rather than fabricating content.
