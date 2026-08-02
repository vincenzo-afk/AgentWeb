# Extractor Spec

## Purpose
Turn raw page content into structured data. See [docs/core/extraction.md](../../docs/core/extraction.md) and [docs/api/reference/extract.md](../../docs/api/reference/extract.md).

## Interface
```
extract(content: RawContent, schema?: Schema) -> StructuredData
```

## Behavior
- Schema-guided mode: constrained to requested fields, returns typed values.
- Best-effort mode (no schema): general-purpose structured representation (title, main text, tables, entities, links).
- Delegates raw parsing to [PARSER_SPEC.md](PARSER_SPEC.md) and field canonicalization to [NORMALIZER_SPEC.md](NORMALIZER_SPEC.md).

## Confidence scoring
Each extracted field carries a confidence score, consumed by [RANKING_SPEC.md](RANKING_SPEC.md) synthesis-readiness checks.
