# Operations Runbook

See [docs/operations/runbooks.md](../../docs/operations/runbooks.md) for the customer-facing/operational incident runbooks (elevated error rate, monitor checks not firing, browser session failures, cost spikes). This spec-side pointer exists so implementers can find operational context from within the `spec/` tree.

## Build-relevant operational hooks
Every module implementation should expose whatever the corresponding runbook step needs to diagnose it — e.g., the Browser module must expose sandbox health/capacity metrics because [docs/operations/runbooks.md](../../docs/operations/runbooks.md) references checking that during a "browser session failures spiking" incident. Cross-check new modules against existing runbook steps during [DONE_DEFINITION.md](../testing/DONE_DEFINITION.md) review.
