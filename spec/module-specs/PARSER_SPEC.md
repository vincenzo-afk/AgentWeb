# Parser Spec

## Purpose
Convert raw fetched content (HTML, PDF, JSON, plain text) into a parsed intermediate representation for [EXTRACTOR_SPEC.md](EXTRACTOR_SPEC.md).

## Interface
```
parse(raw: bytes, content_type: string) -> ParsedDocument
```

## Supported formats
- HTML → DOM tree + readability-style main-content detection
- PDF → text + layout hints (tables, headings)
- JSON → structured passthrough
- Plain text → paragraph/sentence segmentation

## Failure modes
Malformed content / unsupported format → return a minimal `ParsedDocument` with raw text only and a `parse_warnings` list, rather than failing the whole extraction.
