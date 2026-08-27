"""Deterministic, evidence-first synthesis for multi-framework comparisons."""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse
from typing import Any

from .models import Citation, Source
from .ranking import RankedSource


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
    for field in ("title", "description", "author", "publishDate", "uploadDate", "transcript_language"):
        value = media.get(field)
        if value not in (None, ""):
            evidence.append(f"media {field}: {str(value)[:500]}")
    return evidence[:40]


@dataclass(frozen=True)
class FrameworkSpec:
    key: str
    label: str
    aliases: tuple[str, ...]
    host_patterns: tuple[str, ...]


FRAMEWORKS = (
    FrameworkSpec(
        "openai_agents",
        "OpenAI Agents SDK",
        ("openai agents sdk", "openai agents", "agents sdk"),
        ("developers.openai.com", "platform.openai.com", "openai.github.io", "github.com/openai", "openai.com"),
    ),
    FrameworkSpec(
        "claude_agent",
        "Anthropic Claude Agent SDK",
        ("claude agent sdk", "anthropic's claude agent sdk", "anthropic claude", "claude sdk"),
        ("code.claude.com", "docs.claude.com", "platform.claude.com", "github.com/anthropics", "anthropic.com"),
    ),
    FrameworkSpec(
        "google_adk",
        "Google Agent Development Kit (ADK)",
        ("google's agent development kit", "google agent development kit", "google adk", "agent development kit", "adk"),
        ("adk.dev", "google.github.io", "ai.google.dev", "docs.cloud.google.com", "github.com/google", "google.com"),
    ),
    FrameworkSpec(
        "langgraph",
        "LangGraph",
        ("langgraph", "langchain"),
        ("docs.langchain.com", "langchain-ai.github.io", "reference.langchain.com", "github.com/langchain-ai", "langchain.com"),
    ),
    FrameworkSpec(
        "autogen",
        "Microsoft AutoGen",
        ("microsoft autogen", "autogen"),
        ("microsoft.github.io", "github.com/microsoft/autogen", "learn.microsoft.com", "microsoft.com"),
    ),
)

FACETS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("version_release", "Current version / release status", ("version", "release", "changelog", "latest", "released", "v0.")),
    ("architecture", "Core architecture", ("architecture", "agent loop", "graph", "workflow", "runtime", "event-driven", "orchestration")),
    ("tools", "Tool / function calling", ("tool", "function calling", "function tool", "built-in tools", "tool wrapper", "extensions")),
    ("mcp", "MCP support", ("model context protocol", "mcp", "mcpworkbench", "mcp server", "mcp client")),
    ("state", "Memory / state management", ("memory", "context management", "session", "state", "checkpoint", "resume", "persistence")),
    ("multi_agent", "Multi-agent support", ("multi-agent", "multi agent", "subagent", "subagents", "handoff", "agentchat", "agents as tools")),
    ("deployment", "Deployment options", ("deploy", "deployment", "cloud", "vertex", "sandbox", "container", "docker", "platform", "managed")),
    ("limitations", "Major limitations", ("limitation", "requires", "only", "experimental", "deprecated", "not supported", "terms")),
    ("licensing", "Licensing", ("license", "licence", "mit", "apache", "bsd", "commercial terms", "terms of service")),
)


def is_framework_comparison(task: str) -> bool:
    lowered = task.lower()
    mentioned = sum(any(alias in lowered for alias in spec.aliases) for spec in FRAMEWORKS)
    return mentioned >= 2 and bool(re.search(r"\b(compare|comparison|rank|evaluat|frameworks?)\b", lowered))


def comparison_queries(task: str) -> list[str]:
    """Return one targeted official-source query per named framework."""
    lowered = task.lower()
    queries: list[str] = []
    for spec in FRAMEWORKS:
        if any(alias in lowered for alias in spec.aliases):
            queries.append(
                f"{spec.label} official documentation releases changelog current version as of August 2026 "
                "architecture tools function calling MCP memory state multi-agent deployment limitations licensing"
            )
    return queries or [task]


def _matches_pattern(url: str, pattern: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    pattern = pattern.lower().rstrip("/")
    if pattern.startswith("github.com/"):
        return host == "github.com" and parsed.path.lower().startswith("/" + pattern.split("/", 1)[1])
    return host == pattern or host.endswith("." + pattern)


def _framework_for_source(source: Source, task: str) -> FrameworkSpec | None:
    url = source.url
    title_text = f"{source.title} {source.snippet}".lower()
    candidates: list[tuple[int, FrameworkSpec]] = []
    for spec in FRAMEWORKS:
        host_score = max((len(pattern) for pattern in spec.host_patterns if _matches_pattern(url, pattern)), default=0)
        alias_score = max((len(alias) for alias in spec.aliases if alias in title_text), default=0)
        if host_score or alias_score:
            candidates.append((host_score * 10 + alias_score, spec))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1].key))
    return candidates[0][1]


def _evidence_text(source: Source) -> str:
    structured = " ".join(_structured_evidence(source))
    return " ".join([source.title, source.snippet, structured]).strip()


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    return [part.strip(" -") for part in re.split(r"(?<=[.!?])\s+|\s{2,}", normalized) if part.strip()]


def _excerpt_for_facet(sources: list[Source], keywords: tuple[str, ...]) -> tuple[str, Source] | None:
    ranked: list[tuple[int, int, Source, str]] = []
    for source_index, source in enumerate(sources):
        text = _evidence_text(source)
        lowered = text.lower()
        hits = sum(1 for keyword in keywords if keyword in lowered)
        if not hits:
            continue
        sentence = next((item for item in _sentences(text) if any(keyword in item.lower() for keyword in keywords)), text)
        ranked.append((hits, -source_index, source, sentence[:420]))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (-item[0], -item[1]))
    _, _, source, excerpt = ranked[0]
    return excerpt, source


def _official_sources(ranked_sources: list[RankedSource]) -> list[Source]:
    sources: list[Source] = []
    seen: set[str] = set()
    for item in ranked_sources:
        source = item.source
        if source.id in seen:
            continue
        if _framework_for_source(source, "") is not None:
            sources.append(source)
            seen.add(source.id)
    return sources


def _citations_for_lines(answer: str, line_source_ids: list[list[str]]) -> list[Citation]:
    citations: list[Citation] = []
    offset = 0
    lines = answer.splitlines(keepends=True)
    for index, line in enumerate(lines):
        content = line.rstrip("\r\n")
        ids = line_source_ids[index] if index < len(line_source_ids) else []
        if content.strip() and ids:
            citations.append(Citation(claim_span=[offset, offset + len(content)], source_ids=ids))
        offset += len(line)
    return citations


def _reference_marker(source: Source, references: list[Source]) -> str:
    try:
        number = references.index(source) + 1
    except ValueError:
        references.append(source)
        number = len(references)
    return f"[{number}]"


def build_comparison(ranked_sources: list[RankedSource], task: str) -> tuple[str, list[Source], list[Citation], dict[str, Any], float, list[str]]:
    """Build a bounded comparison with explicit unverified cells and URL references."""
    framework_sources: dict[str, list[Source]] = {spec.key: [] for spec in FRAMEWORKS}
    for source in _official_sources(ranked_sources):
        spec = _framework_for_source(source, task)
        if spec is not None:
            framework_sources[spec.key].append(source)
    references: list[Source] = []
    lines: list[str] = []
    line_ids: list[list[str]] = []
    lines.append("## AgentWeb framework comparison")
    line_ids.append([])
    lines.append(f"Scope: {task}")
    line_ids.append([])
    lines.append("")
    line_ids.append([])
    lines.append("Each cell below is an evidence statement, not an inferred fact. A cell marked **Not verified** means the returned official evidence did not support that field.")
    line_ids.append([])
    lines.append("")
    line_ids.append([])

    header = "| Framework | " + " | ".join(label for _, label, _ in FACETS) + " |"
    separator = "|---|" + "---|" * len(FACETS)
    lines.extend([header, separator])
    line_ids.extend([[], []])
    structured_rows: list[dict[str, Any]] = []
    coverage_scores: list[tuple[int, str]] = []

    for spec in FRAMEWORKS:
        sources = framework_sources[spec.key]
        row: list[str] = [spec.label]
        row_ids: list[str] = []
        facet_records: dict[str, Any] = {}
        verified = 0
        for facet_key, _facet_label, keywords in FACETS:
            found = _excerpt_for_facet(sources, keywords)
            if found is None:
                value = "**Not verified**"
                source_ids: list[str] = []
            else:
                excerpt, source = found
                marker = _reference_marker(source, references)
                value = f"{excerpt} {marker}".replace("|", "/")
                source_ids = [source.id]
                verified += 1
                row_ids.extend(source_ids)
            row.append(value[:700])
            facet_records[facet_key] = {"status": "verified" if found else "unverified", "evidence": excerpt if found else "", "source_ids": source_ids}
        lines.append("| " + " | ".join(row) + " |")
        line_ids.append(list(dict.fromkeys(row_ids)))
        coverage_scores.append((verified, spec.key))
        structured_rows.append({"framework": spec.label, "facets": facet_records, "source_ids": [source.id for source in sources]})

    lines.extend(["", "## Evidence-based production ranking", "", "This ranking is a retrieval-coverage heuristic for a production autonomous web-research agent; it is not a performance benchmark. It prioritizes the number of requested dimensions supported by first-party evidence and should remain provisional where evidence is missing.", ""])
    line_ids.extend([[], [], [], [], []])
    ranking = sorted(coverage_scores, key=lambda item: (-item[0], item[1]))
    for position, (verified, key) in enumerate(ranking, 1):
        label = next(spec.label for spec in FRAMEWORKS if spec.key == key)
        lines.append(f"{position}. **{label}** — {verified}/{len(FACETS)} requested dimensions supported by returned first-party evidence.")
        line_ids.append([])

    unverified = [
        f"{next(spec.label for spec in FRAMEWORKS if spec.key == key)}: {', '.join(label for facet_key, label, _ in FACETS if not structured_rows[[row['framework'] for row in structured_rows].index(next(spec.label for spec in FRAMEWORKS if spec.key == key))]['facets'][facet_key]['status'] == 'verified') or 'none'}"
        for _, key in ranking
    ]
    lines.extend(["", "## Explicit verification gaps", ""])
    line_ids.extend([[], [], []])
    for item in unverified:
        lines.append(f"- {item}")
        line_ids.append([])

    lines.extend(["", "## References", ""])
    line_ids.extend([[], [], []])
    for index, source in enumerate(references, 1):
        title = source.title or source.url
        lines.append(f"[{index}]: {source.url} \"{title.replace(chr(34), '')}\"")
        line_ids.append([source.id])

    answer = "\n".join(lines)
    selected_ids = {source.id for source in references}
    considered = [item.source for item in ranked_sources]
    selected_count = len(selected_ids)
    score = round(sum(coverage for coverage, _ in coverage_scores) / max(1, len(coverage_scores) * len(FACETS)), 2)
    structured = {
        "task": task,
        "frameworks": structured_rows,
        "ranking": [{"rank": index, "framework": next(spec.label for spec in FRAMEWORKS if spec.key == key), "verified_dimensions": verified, "total_dimensions": len(FACETS)} for index, (verified, key) in enumerate(ranking, 1)],
        "references": [{"id": source.id, "url": source.url, "title": source.title} for source in references],
        "evidence_gaps": [item for item in unverified if "none" not in item],
        "unverified_policy": "Missing fields are explicitly marked Not verified; no claim is inferred from absence of evidence.",
    }
    return answer, considered, _citations_for_lines(answer, line_ids), structured, score, [item for item in unverified if "none" not in item]
