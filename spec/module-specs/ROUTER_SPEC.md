# Router Spec

## Purpose
Translate a Plan into concrete tool calls and source selections. See [docs/core/router.md](../../docs/core/router.md).

## Interface
```
route(plan: Plan) -> ToolCall[]
```

## Responsibilities
- Map each plan step to a specific execution primitive (Search/Crawl/Browser/Extract).
- Select candidate sources/domains for search and crawl steps.
- Decide static-fetch vs. Browser escalation (see [BROWSER_SPEC.md](BROWSER_SPEC.md) escalation criteria).
- Apply [Connector](CONNECTOR_SPEC.md) overrides where a target matches a known connector pattern.
- Respect [rate limits](../../docs/api/rate-limits.md) and mode-based cost ceilings.

## Failure modes
Selected source unreachable → fall back to next-ranked candidate source per [../resilience/FALLBACKS.md](../resilience/FALLBACKS.md); do not fail the run solely due to one source being unavailable.
