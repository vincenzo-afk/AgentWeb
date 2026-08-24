# Extraction

The extraction layer transforms raw pages into usable structured outputs: text, metadata, tables, lists, entities, prices, dates, links, summaries, and normalized page content. Price normalization recognizes documented INR, USD, EUR, and GBP formats across grouped-digit and decimal-separator conventions; date normalization emits ISO values for ISO, slash/dot/hyphen, and documented English, French, Spanish, and German month-name forms. Unparseable values are retained with `normalized: false` and lower confidence rather than being dropped.

## Modes

- **Schema-guided** — caller supplies a target schema (see [api/reference/extract.md](../api/reference/extract.md)); extraction is constrained to those fields.
- **Best-effort/normalized** — no schema supplied; AgentWeb returns a general-purpose structured representation (title, main text, detected entities, tables, links).

## Inputs

Extraction can run against:
- A single fetched/browsed page
- Pages gathered from a [crawl](../api/reference/crawl.md)
- A stored [snapshot](memory.md)

## Downstream use

Extracted structured data feeds [Ranking](ranking.md), [Knowledge Graph](knowledge-graph.md) updates, and ultimately [Synthesis](synthesis.md).
