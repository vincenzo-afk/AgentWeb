# Object Model

Canonical object definitions referenced throughout the spec.

```
Snapshot { target, hash, content, captured_at }
Diff { target, from_hash, to_hash, changed_fields, summary }
Entity { id, type, name, attributes, sources }
Relation { id, from, to, type, confidence, sources }
Source { id, url, trust_score, cited }
Citation { claim_span, source_ids }
Plan { id, steps, estimated_mode }
ToolCall { type, params }
ExecutionTrace { execution_id, plan, actions, sources_considered, sources_used, trust_scores }
Monitor { id, task, status, frequency, webhook_url, last_checked_at, last_change_at }
```

See [../architecture/DATA_FLOW.md](../architecture/DATA_FLOW.md) for how these objects move through the pipeline, and [ER_DIAGRAM.md](ER_DIAGRAM.md) for the graph-specific detail on `Entity`/`Relation`.
