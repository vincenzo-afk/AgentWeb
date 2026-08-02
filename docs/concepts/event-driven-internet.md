# Event-Driven Internet

A major long-term opportunity is to treat the internet as an event stream rather than only a searchable document collection. In this model, internet changes become triggers: a page changes, a product price drops, a visa slot appears, a repository releases a version, or a policy page is updated — AgentWeb detects the event, updates memory and graph state, triggers a workflow, and delivers the relevant outcome.

This shifts the platform from:

```
Ask -> Answer
```

into:

```
Internet changes -> detection -> graph update -> workflow trigger -> research -> notification -> downstream action
```

This event-oriented approach is a strong path toward category definition because it transforms web intelligence from reactive lookup into proactive infrastructure. It builds directly on the [Memory Model](memory-model.md) (for change detection) and the [Knowledge Model](knowledge-model.md) (for propagating what a change *means* across related entities).

See [roadmap.md](../roadmap.md) Phase 4 and [getting-started/first-monitor.md](../getting-started/first-monitor.md) for the current (pre-full-event-model) building block: `internet.observe()`.
