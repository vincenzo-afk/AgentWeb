# Browser and Scheduler Design

This build slice adds rendered browser execution and durable scheduled monitor checks without introducing a paid provider or weakening the existing trust boundaries.

## Rendered browser

The browser adapter is optional at import time and uses Playwright against a system Chromium binary when available. The core package remains dependency-light; browser-enabled environments install the optional browser extra and provide Chromium through the environment rather than downloading a proprietary runtime as part of the repository.

Each `open` call creates a fresh browser context. Cookies, storage, cache, and session state are not shared between calls. The target URL is passed through the existing Trust Engine before rendering. The context routes outbound requests so the target origin and same-origin resources are allowed while cross-origin HTTP(S) requests are aborted where feasible. Credentials are not accepted in the action payload and are never written to traces.

Action support is intentionally limited to the documented primitives: `click`, `type`, `wait_for`, `scroll`, and `extract`. Every action has a 30-second timeout; the full session has a 90-second deadline. Failed actions are retried once, then returned as a structured partial result with the actions that succeeded and a warning describing the failure.

## Production scheduler

The scheduler uses SQLite as a durable at-least-once job queue. Monitor rows carry `next_run_at`, `lease_until`, `attempts`, and `last_error`; job rows carry priority, status, retry timing, and dead-letter state. Frequency maps to fixed intervals of 60 seconds, 3600 seconds, and 86400 seconds.

A worker claims one due job with a short lease inside a transaction, executes the monitor check, and acknowledges success by scheduling the next occurrence. Transient failures are retried with bounded exponential backoff up to five attempts. Exhausted jobs move to `dead_letter` instead of disappearing. `minutely` jobs have higher priority than `hourly` and `daily` jobs. Re-running an already acknowledged job is idempotent because the monitor check uses immutable snapshots and content hashes.

The scheduler is exposed as a foreground worker and a one-shot `run_once` method. This supports container supervisors, systemd, or managed background processes without silently creating an unbounded thread in the HTTP API process. No scheduler run requires AI judgment; all behavior is deterministic and locally testable.

## Distributed queue coordination

When `AGENTWEB_DISTRIBUTED_QUEUE` is enabled, API and worker instances coordinate through the same PostgreSQL database. Due-job claims use `FOR UPDATE SKIP LOCKED`, expired leases are reclaimed, and every claim receives a unique lease token. Acknowledge, failure, and cancellation transitions require the active lease token, so a stale worker cannot mutate a job after another instance reclaims it. Organization-scoped token buckets for scheduled checks and webhook delivery are stored and consumed under row locks in PostgreSQL; rate-limit failures include a retry interval.

SQLite remains the default local implementation. Distributed mode is explicit, requires a PostgreSQL `DATABASE_URL`, and does not claim full business-record runtime cutover: monitor and delivery state must still be available to the worker's configured local store until the broader relational runtime migration is completed. PostgreSQL bootstrap is idempotent, adds the coordination tables/columns, and the migration map carries lease tokens and limiter state.

## Explicit non-goals

This slice still does not implement CAPTCHA solving, MFA, authenticated credential storage, arbitrary JavaScript injection, cross-organization browser state, a multi-process browser pool, graph reasoning, planner/execute APIs, or workflow automation. Those remain separate security, product, or roadmap decisions.
