# Logging

## Levels
`debug` (local/dev only), `info` (normal operation events), `warn` (degraded-but-handled, e.g., a fallback engaged), `error` (failed operation requiring attention). The `LOG_LEVEL` environment variable sets the minimum emitted severity and defaults to `info`; values outside these four levels fail fast during server construction.

## Required fields
Every log line includes `request_id` or `execution_id` where applicable, `component`, `timestamp`, and `level`, so logs can be correlated with a specific run's [execution trace](TRACING.md).

## What must never be logged
API keys, webhook signing secrets, customer-supplied browser-workflow credentials, or full page content bodies (log a content hash/reference instead) — per [../decisions/INVARIANTS.md](../decisions/INVARIANTS.md) item 6.

## Retention
Logs retained per operational need (typically shorter than [execution trace retention](../../docs/operations/data-retention.md)), since traces are the durable, structured record for a given run.
