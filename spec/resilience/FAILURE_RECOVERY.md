# Failure Recovery

## Run-level recovery
A `solve` run entering `failed` state (see [../architecture/STATE_MACHINE.md](../architecture/STATE_MACHINE.md)) should still return whatever partial execution trace exists, so the caller can inspect what happened via [../../docs/getting-started/debugging-basics.md](../../docs/getting-started/debugging-basics.md), rather than returning an opaque failure.

## Monitor-level recovery
A monitor experiencing repeated `check_failed` events (see [FAILURE_MODES.md](FAILURE_MODES.md)) does not auto-cancel; it continues attempting on schedule and surfaces a degraded-health signal via `GET /observe/{id}`, requiring explicit customer or operator action to pause/cancel.

## System-level recovery
See [../../docs/operations/disaster-recovery.md](../../docs/operations/disaster-recovery.md) for infrastructure-level recovery (regional outage, store loss).

## Principle
Prefer partial, honestly-labeled results over total failure wherever the missing piece doesn't invalidate the whole result's trustworthiness.
