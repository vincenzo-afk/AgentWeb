# Normalizer Spec

## Purpose
Canonicalize extracted fields into consistent types/formats before they reach [RANKING_SPEC.md](RANKING_SPEC.md), [GRAPH_SPEC.md](GRAPH_SPEC.md), or [SYNTHESIS_SPEC.md](SYNTHESIS_SPEC.md).

## Interface
```
normalize(field: RawField, expected_type: string) -> NormalizedField
```

## Examples of normalization rules
- Prices → numeric value + ISO currency code, regardless of source formatting (`₹42,999` → `{ value: 42999, currency: "INR" }`). The local normalizer recognizes INR, USD, EUR, and GBP symbols/codes, grouped digits, decimal comma/dot conventions, non-breaking spaces, and accounting-style negative parentheses.
- Dates → ISO 8601, regardless of source locale/format. The local normalizer accepts ISO timestamps, common slash/dot/hyphen forms, and English, French, Spanish, and German month names.
- Entity names → deduplicated canonical form for [GRAPH_SPEC.md](GRAPH_SPEC.md) linking (e.g., resolving "Company X Inc." and "Company X" to one entity)

## Failure modes
Unparseable value → retain raw string with a `normalized: false` flag rather than dropping the field. Normalization remains deterministic and does not infer an ambiguous locale beyond the documented parsing order; the confidence score is lower for values that remain raw.
