# Data Flow

## Shapes of data moving through the pipeline

| Stage | Input | Output |
|---|---|---|
| Planner | Task text, mode hint, available skills | Plan (ordered steps) |
| Router | Plan | Tool calls with concrete targets/sources |
| Search/Crawl/Browser | URLs or queries | Raw page content, links |
| Extract/Parser/Normalizer | Raw page content | Structured fields |
| Memory | Target + new content | Snapshot record, diff (if prior snapshot exists) |
| Graph | Extracted entities/relations | Updated graph nodes/edges |
| Ranking | Sources + extracted content | Trust-scored, ranked evidence set |
| Synthesis | Ranked evidence | Answer text + citations |

See [../data/OBJECT_MODEL.md](../data/OBJECT_MODEL.md) for the canonical schema of each object referenced here, and [EVENT_FLOW.md](EVENT_FLOW.md) for the async/monitor-specific data path.
