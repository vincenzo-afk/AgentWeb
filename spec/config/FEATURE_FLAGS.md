# Feature Flags

| Flag | Purpose | Default |
|---|---|---|
| `graph_layer_enabled` | Gates the Phase 2 [Knowledge Graph](../module-specs/GRAPH_SPEC.md) | off (pre-GA) |
| `agent_apis_enabled` | Gates Phase 3 `plan`/`execute`/`diff`/`report` endpoints | off (pre-GA) |
| `websocket_streaming_enabled` | Gates [../api/WEBSOCKET_API.md](../api/WEBSOCKET_API.md) | off |
| `memory_reuse_enabled` | Allows disabling memory reuse for debugging/testing | on |
| `custom_rankers_enabled` | Gates [docs/guides/custom-rankers.md](../../docs/guides/custom-rankers.md) per-org | on (enterprise tier) |

Flags gating unfinished capabilities (`graph_layer_enabled`, `agent_apis_enabled`) should default off until the corresponding [roadmap.md](../../docs/roadmap.md) phase reaches GA, and be flippable per-organization for early access.
