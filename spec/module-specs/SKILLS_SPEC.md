# Skills Spec

## Purpose
Reusable strategy templates for recurring task classes. See [docs/concepts/internet-skills.md](../../docs/concepts/internet-skills.md) and [docs/guides/creating-skills.md](../../docs/guides/creating-skills.md).

## Interface
```
Skill {
  name: string
  description: string
  input_schema: Schema
  plan_template: PlanTemplate
}
register_skill(skill: Skill) -> void
match_skill(task: string) -> Skill | null
```

## Matching
Skill matching uses task-similarity classification against registered skill descriptions; ties are broken toward the skill with the higher historical success rate (see [../../docs/research/economic-model.md](../../docs/research/economic-model.md) learning-loop discussion).

## Promotion to built-in library
Skills with consistently high output quality and low cost across many organizations are candidates for promotion into AgentWeb's built-in skill library, subject to privacy review (no organization-specific task content is generalized without consent).
