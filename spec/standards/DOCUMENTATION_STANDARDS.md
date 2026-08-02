# Documentation Standards

- Every module spec ([../module-specs/](../module-specs/)) documents: purpose, interface, behavior/algorithm summary, and failure modes, at minimum.
- Every doc cross-links to related docs rather than duplicating their content — prefer "see X" over copy-pasting.
- Prose usage docs live in `docs/`; build specs live in `spec/`; the two should never contradict each other. If they appear to, `spec/` is the source of truth for implementation behavior and `docs/` should be updated to match.
- Diagrams use fenced code blocks (ASCII or Mermaid) rather than binary image files where possible, so they stay diffable in version control — see [../architecture/COMPONENT_DIAGRAM.md](../architecture/COMPONENT_DIAGRAM.md) for the pattern.
