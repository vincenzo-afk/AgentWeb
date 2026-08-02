# Plugin API

## Registration interface
```
register_plugin({
  type: "connector" | "skill" | "ranker",
  match: (context) => bool,
  hooks: { ... type-specific handlers ... }
})
```

## Connector-type hooks
`extraction_hints`, `interaction_script`, `ranking_bias` — see [../module-specs/CONNECTOR_SPEC.md](../module-specs/CONNECTOR_SPEC.md).

## Skill-type hooks
`plan_template`, `input_schema` — see [../module-specs/SKILLS_SPEC.md](../module-specs/SKILLS_SPEC.md).

## Ranker-type hooks
`score_override(source, task_context) -> float` — see [../module-specs/RANKING_SPEC.md](../module-specs/RANKING_SPEC.md).

## Versioning
Plugin API changes follow the same [../api/VERSIONING.md](../api/VERSIONING.md) policy as the public REST API — breaking changes require a major version bump.
