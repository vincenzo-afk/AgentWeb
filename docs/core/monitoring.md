# Monitoring

Implements ongoing observation of pages, entities, product listings, policy pages, docs, releases, or mentions, producing alerts or triggering downstream workflows on change.

## Lifecycle

1. A monitor is created via [`/observe`](../api/reference/monitor.md) with a task description and optional frequency.
2. The scheduler runs periodic checks against the target(s), using [Memory](memory.md) to snapshot and hash current state.
3. The diff engine compares the new snapshot to the last known one.
4. If a meaningful change is detected (per task-specific change criteria), an alert is delivered via [webhook](../api/webhooks.md) or made available via polling.

## Frequency and cost

Check frequency (`minutely`, `hourly`, `daily`) trades off responsiveness against cost; see [operations/cost-controls.md](../operations/cost-controls.md).

## Relationship to the event-driven model

Monitoring is the current building block toward the longer-term [event-driven internet model](../concepts/event-driven-internet.md), where detected changes eventually trigger richer downstream workflows automatically rather than only delivering an alert.
