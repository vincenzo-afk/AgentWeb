# Synthesis

The synthesis layer produces grounded outputs — cited answers, comparisons, reports, summaries, timelines, or structured JSON — using evidence gathered from the lower layers. This is the user-facing stage where intelligence becomes usable in applications.

## Inputs

- Ranked, trust-scored sources (from [Ranking](ranking.md))
- Extracted structured data (from [Extraction](extraction.md))
- Relevant graph context, where available (from [Knowledge Graph](knowledge-graph.md))

## Output guarantees

- Every claim in a synthesized answer should be traceable to at least one cited source (see [api/citations.md](../api/citations.md)).
- Output format adapts to the task: free-text answer, structured comparison table, timeline, or raw JSON depending on what the task implies or what `output_format` requests.

## Failure handling

If evidence is insufficient or conflicting, synthesis should surface that uncertainty explicitly (e.g., noting disagreement between sources) rather than silently picking one version — consistent with the [trust model](../concepts/trust-model.md).
