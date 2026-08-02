# Terminology (API-Level)

This page covers terms as they appear specifically in API requests, responses, and configuration. For conceptual definitions, see [GLOSSARY.md](../GLOSSARY.md) at the repository root and [concepts/index.md](concepts/index.md).

| Term | Meaning in API context |
|---|---|
| `task` | The natural-language or structured description of intent passed to `internet.solve()` or `internet.observe()`. |
| `mode` | One of `flash`, `focus`, `dive`, `monitor` — controls retrieval depth. |
| `run` | A single execution instance of a task, with its own execution graph and identifiers. |
| `plan` | The planner's output describing the intended strategy for a run. |
| `source` | A single evidence unit (a page, document, or dataset) referenced in a result. |
| `citation` | A structured reference linking a claim in the output to a specific source. |
| `trust_score` | A numeric or categorical rating of a source's reliability. |
| `snapshot` | A stored capture of a target's state at a point in time. |
| `diff` | The computed difference between two snapshots. |
| `monitor` | A recurring, scheduled task that watches a target and triggers alerts on change. |
| `webhook` | An HTTP callback used to deliver monitor alerts or async run completions. |
| `skill` | A reusable strategy template for a recurring class of task. |
| `execution_graph` | The full inspectable record of a run's plan and actions. |

See [api/index.md](api/index.md) for how these terms map onto request/response schemas.
