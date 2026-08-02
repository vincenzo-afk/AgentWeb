# Module Dependencies

Full pairwise dependency list (module → hard dependency, must be functional first):

| Module | Depends on |
|---|---|
| Crawler | Search, Parser |
| Extractor | Parser, Normalizer |
| Ranking | Trust Engine |
| Connector | (none — but Browser needs it) |
| Browser | Connector |
| Skills | (none) |
| Planner | Skills |
| Router | Planner, Connector |
| Monitor | Memory, Router, Alerting |
| Graph | Extractor, Normalizer, Memory |
| Synthesis | Ranking, Memory; Graph optional |
| Alerting | Memory (diff output) |

See [../architecture/DEPENDENCY_GRAPH.md](../architecture/DEPENDENCY_GRAPH.md) for the diagrammatic version and [BUILD_ORDER.md](BUILD_ORDER.md) for the resulting build sequence.
