# Normalizer Spec

## Purpose
Canonicalize extracted fields into consistent types/formats before they reach [RANKING_SPEC.md](RANKING_SPEC.md), [GRAPH_SPEC.md](GRAPH_SPEC.md), or [SYNTHESIS_SPEC.md](SYNTHESIS_SPEC.md).

## Interface
```
normalize(field: RawField, expected_type: string) -> NormalizedField
```

## Examples of normalization rules
- Prices → numeric value + ISO currency code, regardless of source formatting (`₹42,999` → `{ value: 42999, currency: "INR" }`)
- Dates → ISO 8601, regardless of source locale/format
- Entity names → deduplicated canonical form for [GRAPH_SPEC.md](GRAPH_SPEC.md) linking (e.g., resolving "Company X Inc." and "Company X" to one entity)

## Failure modes
Unparseable value → retain raw string with a `normalized: false` flag rather than dropping the field.
