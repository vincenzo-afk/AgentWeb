# API Reference

AgentWeb exposes a REST API (with JavaScript and Python SDK wrappers) organized around the outcome-first model described in [concepts/outcomes-over-tools.md](../concepts/outcomes-over-tools.md).

## Primary endpoints

| Endpoint | Purpose |
|---|---|
| [`solve`](reference/solve.md) | One-shot grounded research/synthesis |
| [`observe`](reference/monitor.md) | Recurring monitoring with change alerts |
| [`search`](reference/search.md) | Low-level search primitive |
| [`crawl`](reference/crawl.md) | Low-level structured traversal primitive |
| [`browser`](reference/browser.md) | Low-level browser session primitive |
| [`extract`](reference/extract.md) | Low-level structured extraction primitive |
| [`memory`](reference/memory.md) | Direct access to stored snapshots/diffs |
| [`graph`](reference/graph.md) | Direct access to the knowledge graph |
| [`agents`](reference/agents.md) | Agent-native plan/execute/observe/diff/report |
| [`admin`](reference/admin.md) | Organization, key, and usage management |

## Cross-cutting topics

- [Authentication](authentication.md)
- [Versioning](versioning.md)
- [Endpoints overview](endpoints.md)
- [Requests](requests.md)
- [Responses](responses.md)
- [Errors](errors.md)
- [Rate limits](rate-limits.md)
- [Webhooks](webhooks.md)
- [Idempotency](idempotency.md)
- [Pagination](pagination.md)
- [Filtering](filtering.md)
- [Citations](citations.md)
- [Examples](examples.md)

For a machine-readable spec, see [openapi/openapi.yaml](../../openapi/openapi.yaml).
