# Component Diagram

```
                 ┌─────────────┐
   Client ──────▶│  API Tier   │
                 └──────┬──────┘
                        ▼
                 ┌─────────────┐
                 │   Planner   │
                 └──────┬──────┘
                        ▼
                 ┌─────────────┐
                 │   Router    │
                 └──────┬──────┘
        ┌───────────────┼───────────────┬─────────────┐
        ▼               ▼               ▼             ▼
   ┌─────────┐    ┌───────────┐   ┌───────────┐  ┌───────────┐
   │ Search  │    │  Crawler  │   │  Browser  │  │  Extract  │
   └────┬────┘    └─────┬─────┘   └─────┬─────┘  └─────┬─────┘
        └───────────────┴───────────────┴──────────────┘
                        ▼
                 ┌─────────────┐
                 │   Memory    │
                 └──────┬──────┘
                        ▼
                 ┌─────────────┐
                 │    Graph    │
                 └──────┬──────┘
                        ▼
                 ┌─────────────┐
                 │   Ranking   │
                 └──────┬──────┘
                        ▼
                 ┌─────────────┐
                 │  Synthesis  │
                 └──────┬──────┘
                        ▼
                     Response
```

Each box corresponds to a module documented in [../module-specs/](../module-specs/). See [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) for the underlying build/runtime dependency relationships.
