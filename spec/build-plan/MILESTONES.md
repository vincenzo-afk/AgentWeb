# Milestones

| Milestone | Exit criteria |
|---|---|
| M0: MVP live | `/solve` and `/observe` functional end-to-end; citation coverage and trust scoring meet [../product/SUCCESS_METRICS.md](../product/SUCCESS_METRICS.md) targets on a representative task set |
| M1: Depth & Modes | Crawler and Browser in production; all four [retrieval modes](../../docs/concepts/retrieval-modes.md) available and meeting [../testing/PERFORMANCE_TARGETS.md](../testing/PERFORMANCE_TARGETS.md) |
| M2: Graph GA | Graph queries answer representative multi-hop questions correctly on sampled evaluation set; `graph_layer_enabled` flag defaults on |
| M3: Agent APIs GA | `plan`/`execute`/`diff`/`report` stable and documented; at least one reference agent integration built ([examples/research-agent](../../examples/research-agent)) |
| M4: Event-driven pilot | At least one workflow-trigger integration live beyond simple webhook alerting |

Each milestone requires the corresponding [testing](../testing/) acceptance criteria to pass before being marked complete.
