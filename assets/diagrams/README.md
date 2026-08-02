# Diagrams

This folder is for architecture and flow diagrams referenced from the docs (currently represented as inline ASCII/Mermaid in the docs themselves, e.g. [architecture.md](../../docs/architecture.md)).

Suggested diagrams to add here as the project matures:

- `execution-pipeline.svg` — the intent → planner → router → execution → memory → graph → ranking → synthesis → report flow
- `memory-lifecycle.svg` — snapshot → hash → compare → reuse → refresh
- `event-driven-model.svg` — internet change → detection → graph update → workflow trigger → notification
- `retrieval-modes.svg` — Flash/Focus/Dive/Monitor depth-vs-cost comparison

Keep source files (e.g. `.excalidraw`, `.drawio`) alongside exported `.svg`/`.png` versions so diagrams can be edited, not just viewed.
