# Control Flow

## Branching logic in the `solve` pipeline

- **Mode not specified** → Planner selects mode based on task classification (see [../module-specs/PLANNER_SPEC.md](../module-specs/PLANNER_SPEC.md)).
- **Skill matched** → Router follows the skill's plan template rather than freeform planning.
- **Static fetch insufficient** → Router escalates to Browser (see [../module-specs/BROWSER_SPEC.md](../module-specs/BROWSER_SPEC.md)).
- **Memory hit (unchanged)** → skip re-fetch/re-extraction for that target, reuse prior extraction.
- **Source fails/times out** → retry per [../resilience/RETRY_POLICY.md](../resilience/RETRY_POLICY.md); if exhausted, exclude source and continue with remaining evidence rather than failing the whole run.
- **Insufficient evidence for synthesis** → Synthesis surfaces uncertainty explicitly rather than fabricating a confident answer (see [../module-specs/SYNTHESIS_SPEC.md](../module-specs/SYNTHESIS_SPEC.md)).

See [../resilience/FAILURE_MODES.md](../resilience/FAILURE_MODES.md) for the full failure taxonomy these branches guard against.
