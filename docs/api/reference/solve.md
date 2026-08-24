# `POST /solve`

The primary outcome-first endpoint. Describe a task; AgentWeb plans and executes the necessary search, browsing, extraction, and synthesis, returning a grounded, cited answer.

## Request

```json
{
  "task": "Find the cheapest RTX 6090 currently available in India and cite trustworthy sources",
  "mode": "dive",
  "output_format": "comparison",
  "graph_query": {
    "related_to": "Acme",
    "depth": 2,
    "limit": 20
  },
  "webhook_url": "https://myapp.example.com/webhooks/agentweb",
  "idempotency_key": "optional-client-uuid"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `task` | string | yes | Natural-language intent |
| `mode` | string | no | `flash`, `focus`, `dive` (planner chooses if omitted) |
| `output_format` | string | no | `text`, `comparison`, `timeline`, or `json`; defaults to `text` |
| `skill` | string | no | Use a named [Internet Skill](../../concepts/internet-skills.md) instead of freeform planning |
| `inputs` | object | no | Structured skill inputs; for an absolute-URL render or interaction task, may contain the bounded browser `actions` array and opaque `credential_id` or `session_state_id` references. It may also contain `graph_query` with `entity_type`, `related_to`, `relation`, `depth` (1–3), and `limit` (1–100). |
| `graph_query` | object | no | Convenience top-level form of `inputs.graph_query`; graph nodes and edges are converted into grounded graph sources before synthesis. |
| `webhook_url` | string | no | Callback for async delivery on long `dive` runs |
| `idempotency_key` | string | no | See [idempotency.md](../idempotency.md) |

## Response

See [responses.md](../responses.md) and [citations.md](../citations.md) for the full answer/sources/citations shape.
 Responses also include `evidence_score`, `output_format`, `conflicts`, `structured_output`, and additive execution-transparency fields: a sanitized `plan`, `selection_logic`, and bounded `actions` summary. These fields expose intent, selected strategy, tool stages, counts, selected source IDs, and evidence metrics without returning task parameters, credentials, cookies, or raw page content. When evidence is empty or below the deterministic threshold, `insufficient_evidence` is `true` and citations are omitted. When sources disagree on detected prices or availability, the response surfaces the competing observations instead of silently selecting one. If the task explicitly requests rendering or interaction and includes an absolute URL, the planner routes that URL through the isolated browser engine; invalid opaque credential or session-state references fail closed rather than falling back to an unauthenticated browser context.
