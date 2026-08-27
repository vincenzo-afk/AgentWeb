"""Intent-aware quality gates used by retrieval and ranking."""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from .models import Source


_OFFICIAL_TARGETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("model context protocol", ("modelcontextprotocol.io", "github.com/modelcontextprotocol")),
    ("mcp specification", ("modelcontextprotocol.io", "github.com/modelcontextprotocol")),
    ("openai agents sdk", ("developers.openai.com", "openai.github.io", "github.com/openai")),
    ("openai agents", ("developers.openai.com", "openai.github.io", "github.com/openai")),
    ("claude agent sdk", ("code.claude.com", "platform.claude.com", "github.com/anthropics")),
    ("anthropic claude agent sdk", ("code.claude.com", "platform.claude.com", "github.com/anthropics")),
    ("google agent development kit", ("adk.dev", "ai.google.dev", "github.com/google")),
    ("google adk", ("adk.dev", "ai.google.dev", "github.com/google")),
    ("langgraph", ("docs.langchain.com", "langchain-ai.github.io", "github.com/langchain-ai")),
    ("autogen", ("microsoft.github.io", "github.com/microsoft/autogen")),
    ("python asyncio", ("docs.python.org", "python.org")),
    ("asyncio documentation", ("docs.python.org", "python.org")),
)


@dataclass(frozen=True)
class FactualGate:
    required: bool
    supported: bool
    reason: str


def official_target_hosts(task: str) -> tuple[str, ...]:
    lowered = task.lower()
    matches: list[str] = []
    for phrase, hosts in sorted(_OFFICIAL_TARGETS, key=lambda item: len(item[0]), reverse=True):
        if phrase in lowered:
            matches.extend(hosts)
    return tuple(dict.fromkeys(matches))


def host_matches(url: str, hosts: tuple[str, ...]) -> bool:
    hostname = (urlparse(url).hostname or "").lower().rstrip(".")
    return any(hostname == host or hostname.endswith("." + host) for host in hosts)


def is_official_intent(task: str) -> bool:
    lowered = task.lower()
    return bool(re.search(r"\b(?:official|documentation|docs|reference|api|sdk|guide|specification|changelog|release)\b", lowered))


def _evidence_text(source: Source) -> str:
    pieces = [source.title, source.snippet, source.url]
    data = source.structured_data or {}
    for key in ("evidence_segments", "connector_fields"):
        values = data.get(key)
        if isinstance(values, dict):
            pieces.extend(str(value) for value in values.values())
    return " ".join(pieces)


def factual_gate(task: str, sources: list[Source]) -> FactualGate:
    lowered = task.lower()
    if not re.search(r"\b(?:what is|who is|capital|population|currency|flag|boiling point|temperature|how many|when was)\b", lowered):
        return FactualGate(False, True, "not_a_factual_intent")
    text = " ".join(_evidence_text(source) for source in sources)
    if "boiling point" in lowered:
        supported = bool(re.search(r"\b(?:100\s*(?:°|degrees?)?\s*c|212\s*(?:°|degrees?)?\s*f)\b", text, re.I))
        return FactualGate(True, supported, "boiling_point_value_found" if supported else "boiling_point_value_not_found")
    if re.search(r"\bcapital\s+of\b", lowered):
        supported = bool(re.search(r"\bcapital\b.{0,160}\b(?:is|was|are|equals)\b", text, re.I))
        return FactualGate(True, supported, "capital_claim_found" if supported else "capital_claim_not_found")
    if re.search(r"\bpopulation\b", lowered):
        supported = bool(re.search(r"\bpopulation\b.{0,120}\b\d[\d,.]*\b", text, re.I))
        return FactualGate(True, supported, "population_value_found" if supported else "population_value_not_found")
    return FactualGate(True, bool(text.strip()), "topic_evidence_present" if text.strip() else "claim_evidence_not_found")
