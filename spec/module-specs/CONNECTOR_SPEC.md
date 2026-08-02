# Connector Spec

## Purpose
Site-specific extraction/interaction logic layered on top of generic Search/Browser/Extract behavior. See [docs/guides/building-connectors.md](../../docs/guides/building-connectors.md).

## Interface
```
Connector {
  match(url: string) -> bool
  extraction_hints?: Schema
  interaction_script?: Action[]
  ranking_bias?: { boost?: string[], penalize?: string[] }
}
```

## Registration
Connectors are registered with a URL/domain match pattern; the [Router](ROUTER_SPEC.md) checks for a matching connector before falling back to generic handling.

## Priority
When multiple connectors could match, the most specific pattern (longest matching path prefix) wins.
