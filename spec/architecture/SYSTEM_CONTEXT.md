# System Context

## External actors

- **Developers/applications** — call the AgentWeb API directly or via [SDKs](../../docs/sdk/index.md).
- **AI agents** — use agent-native primitives ([../module-specs/](../module-specs/) plan/execute/observe/diff/report).
- **Third-party websites** — the systems AgentWeb searches, crawls, browses, and extracts from. AgentWeb does not control these and must handle their unreliability gracefully (see [../resilience/FAILURE_MODES.md](../resilience/FAILURE_MODES.md)).
- **Webhook receivers** — customer-owned endpoints receiving monitor alerts (see [../../docs/api/webhooks.md](../../docs/api/webhooks.md)).

## System boundary

AgentWeb owns: API tier, orchestration, execution workers, memory/graph stores, ranking/synthesis, job scheduling, observability. AgentWeb does not own: the content or availability of third-party sites, or customer infrastructure receiving webhooks.

See [NETWORK_ARCHITECTURE.md](NETWORK_ARCHITECTURE.md) for the network-level view of this boundary.
