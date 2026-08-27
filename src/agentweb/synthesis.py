"""Deterministic, citation-safe synthesis over ranked sources."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from typing import Any

from .models import Citation, Source
from .ranking import RankedSource


SUPPORTED_OUTPUT_FORMATS = {"text", "comparison", "timeline", "json"}
_PRICE_RE = re.compile(r"(?:₹|\$|€|£)\s?\d[\d,]*(?:\.\d+)?")
_AVAILABILITY_RE = re.compile(r"\b(in stock|out of stock|available|unavailable|sold out)\b", re.IGNORECASE)


@dataclass
class SynthesisResult:
    answer: str
    sources: list[Source]
    citations: list[Citation]
    insufficient_evidence: bool
    output_format: str = "text"
    evidence_score: float = 0.0
    conflicts: list[dict[str, Any]] | None = None
    structured_output: dict[str, Any] | None = None


def _structured_evidence(source: Source) -> list[str]:
    data = source.structured_data or {}
    evidence: list[str] = []
    for entity in data.get("entities", [])[:10]:
        if str(entity).strip():
            evidence.append(f"entity: {str(entity).strip()}")
    for table_index, table in enumerate(data.get("tables", [])[:5], start=1):
        for row in table[:8]:
            values = [str(value).strip() for value in row if str(value).strip()]
            if values:
                evidence.append(f"table {table_index}: " + " | ".join(values[:12]))
    media = data.get("media") if isinstance(data.get("media"), dict) else {}
    for field in ("title", "description", "author", "channelId", "publishDate", "uploadDate", "lengthSeconds", "viewCount", "transcript_language"):
        value = media.get(field)
        if value not in (None, ""):
            evidence.append(f"media {field}: {str(value)[:500]}")
    transcript = media.get("transcript")
    if isinstance(transcript, str) and transcript.strip():
        evidence.append("media transcript: " + transcript[:2_000])
    return evidence[:40]


def _signals(source: Source) -> list[tuple[str, str]]:
    structured_text = " ".join(_structured_evidence(source))
    text = f"{source.title} {source.snippet} {structured_text}"
    signals = [("price", match.group(0)) for match in _PRICE_RE.finditer(text)]
    signals.extend(("availability", match.group(1).lower()) for match in _AVAILABILITY_RE.finditer(text))
    return signals


def _conflicts(sources: list[Source]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for source in sources:
        for kind, value in _signals(source):
            grouped.setdefault(kind, []).append({"source_id": source.id, "value": value})
    conflicts = []
    for kind, observations in grouped.items():
        distinct = {item["value"].lower() for item in observations}
        if len(distinct) > 1:
            conflicts.append({"field": kind, "observations": observations})
    return conflicts


def _evidence_score(ranked_sources: list[RankedSource], selected: list[Source]) -> float:
    if not ranked_sources or not selected:
        return 0.0
    average = sum(item.score for item in ranked_sources if item.source.id in {source.id for source in selected}) / len(selected)
    coverage = sum(1 for source in selected if source.snippet.strip() or source.title.strip()) / len(selected)
    return round(max(0.0, min(1.0, 0.7 * average + 0.3 * coverage)), 2)


def _render_text(task: str, sources: list[Source], conflicts: list[dict[str, Any]]) -> str:
    answer = (
        f"AgentWeb reviewed {len(sources)} source(s) for this task: {task}\n\n"
        + "\n".join(
            f"{index}. {source.title or source.url} — {source.snippet[:700]}"
            + ("\n" + "\n".join(f"   {source.id}: {claim}" for claim in _structured_evidence(source)) if _structured_evidence(source) else "")
            for index, source in enumerate(sources, start=1)
        )
    )
    if conflicts:
        answer += "\n\nConflicting evidence was detected: " + "; ".join(
            f"{item['field']} values differ across " + ", ".join(observation["source_id"] for observation in item["observations"])
            for item in conflicts
        ) + "."
    return answer


def _render_comparison(task: str, sources: list[Source], conflicts: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    rows = ["| Source | Trust | Evidence |", "|---|---:|---|"]
    items = []
    for source in sources:
        label = source.title or source.url
        evidence = source.snippet.replace("|", "\\|")[:700]
        rows.append(f"| {label} | {source.trust_score:.2f} | {evidence} |")
        items.append({"source_id": source.id, "title": source.title, "url": source.url, "trust_score": source.trust_score, "evidence": source.snippet[:700], "structured_evidence": _structured_evidence(source)})
    if conflicts:
        rows.append("")
        rows.append("**Conflicts:** " + "; ".join(item["field"] for item in conflicts))
    return f"Comparison for: {task}\n\n" + "\n".join(rows), {"task": task, "sources": items, "conflicts": conflicts}


def _render_timeline(task: str, sources: list[Source], conflicts: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    items = [{"source_id": source.id, "label": source.title or source.url, "evidence": source.snippet[:700], "structured_evidence": _structured_evidence(source)} for source in sources]
    answer = f"Timeline-style evidence for: {task}\n\n" + "\n".join(
        f"{index}. {item['label']} — {item['evidence']}" for index, item in enumerate(items, start=1)
    )
    if conflicts:
        answer += "\n\nUncertainty: multiple sources report different values; review the cited evidence before acting."
    return answer, {"task": task, "items": items, "conflicts": conflicts}


def _claim_citations(answer: str, selected: list[Source]) -> list[Citation]:
    """Map each non-empty rendered line to source IDs with exact answer offsets."""
    source_ids = sorted(source.id for source in selected)
    citations: list[Citation] = []
    offset = 0
    for line in answer.splitlines(keepends=True):
        content = line.rstrip("\\r\\n")
        if content.strip():
            ids = source_ids
            match = re.match(r"^\\s*(\\d+)\\.\\s", content)
            if match:
                index = int(match.group(1)) - 1
                ids = [selected[index].id] if 0 <= index < len(selected) else source_ids
            else:
                matching_ids = [source.id for source in selected if f"{source.id}:" in content]
                if matching_ids:
                    ids = matching_ids
            citations.append(Citation(claim_span=[offset, offset + len(content)], source_ids=ids))
        offset += len(line)
    return citations


def synthesize(ranked_sources: list[RankedSource], task: str, output_format: str = "text") -> SynthesisResult:
    """Produce a deterministic answer whose claims are covered by source citations."""
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError("output_format must be one of: text, comparison, timeline, json")
    considered = [item.source for item in ranked_sources]
    selected = [item.source for item in ranked_sources if item.include and (item.source.snippet.strip() or item.source.title.strip())][:10]
    score = _evidence_score(ranked_sources, selected)
    if not selected or score < 0.25:
        return SynthesisResult(
            answer=f"No sufficiently reliable evidence was available for this task: {task}.",
            sources=[replace(source, cited=False) for source in considered],
            citations=[],
            insufficient_evidence=True,
            output_format=output_format,
            evidence_score=score,
            conflicts=[],
            structured_output={},
        )

    conflicts = _conflicts(selected)
    if output_format == "text":
        answer = _render_text(task, selected, conflicts)
        structured: dict[str, Any] = {}
    elif output_format == "comparison":
        answer, structured = _render_comparison(task, selected, conflicts)
    elif output_format == "timeline":
        answer, structured = _render_timeline(task, selected, conflicts)
    else:
        structured = {
            "task": task,
            "sources": [{"id": source.id, "url": source.url, "title": source.title, "snippet": source.snippet[:700], "structured_evidence": _structured_evidence(source)} for source in selected],
            "conflicts": conflicts,
        }
        answer = json.dumps(structured, ensure_ascii=False, sort_keys=True)

    selected_ids = {source.id for source in selected}
    sources = [replace(source, cited=source.id in selected_ids) for source in considered]
    citations = _claim_citations(answer, selected)
    return SynthesisResult(
        answer=answer,
        sources=sources,
        citations=citations,
        insufficient_evidence=False,
        output_format=output_format,
        evidence_score=score,
        conflicts=conflicts,
        structured_output=structured,
    )
