# Plugin Contract

Rules every plugin (connector, skill, or custom ranker) must satisfy to be registered:

1. `match` must be a pure, side-effect-free predicate — no network calls, no mutation.
2. Hook execution must complete within a bounded time budget (see [../resilience/TIMEOUT_POLICY.md](../resilience/TIMEOUT_POLICY.md)); exceeding it causes the plugin to be skipped for that call, falling back to default behavior, not failing the run.
3. Hooks must not access data outside the current request's organization scope.
4. A failing/erroring plugin must degrade gracefully (see [../resilience/FALLBACKS.md](../resilience/FALLBACKS.md)) — a broken custom ranker should never take down a `solve` call, only cause it to fall back to default ranking.
5. Plugins are versioned and org-scoped; a plugin update does not retroactively alter already-completed [execution traces](../observability/TRACING.md).
