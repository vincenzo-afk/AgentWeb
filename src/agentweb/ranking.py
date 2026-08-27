"""Deterministic source ranking for the Phase 0/1 evidence pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from urllib.parse import urlparse

from .models import Source
from .plugins import PluginRegistry


@dataclass
class RankedSource:
    source: Source
    score: float
    include: bool = True


_OFFICIAL_DOCUMENTATION_HOSTS = {
    "platform.claude.com", "docs.claude.com", "anthropic.com",
    "platform.openai.com", "developers.openai.com", "openai.github.io", "openai.com",
    "google.github.io", "ai.google.dev", "adk.dev",
    "langchain-ai.github.io", "python.langchain.com", "docs.langchain.com", "langchain.com",
    "microsoft.github.io", "modelcontextprotocol.io", "docs.github.com", "docs.python.org",
}


_QUESTION_STOPWORDS = {
    "what", "which", "who", "when", "where", "why", "how", "the", "this", "that", "with",
    "from", "into", "about", "does", "do", "can", "could", "should", "would", "will", "have",
    "has", "been", "being", "are", "was", "were", "is", "of", "for", "and", "or", "to", "in",
    "on", "at", "by", "an", "a", "as", "it", "its", "their", "they", "them", "versus", "vs",
}


def _relevance(source: Source, task_context: str) -> float:
    terms = {term.lower().strip(".,?!:;()[]{}\"") for term in task_context.split() if len(term.strip(".,?!:;()[]{}\"")) > 3 and term.lower().strip(".,?!:;()[]{}\"") not in _QUESTION_STOPWORDS}
    haystack = f"{source.title} {source.snippet} {source.url}".lower()
    if not terms:
        return 0.5
    return min(1.0, sum(term in haystack for term in terms) / max(1, min(len(terms), 5)))


def _recency(source: Source) -> float:
    if not source.published_at:
        return 0.5
    try:
        published = datetime.fromisoformat(source.published_at.replace("Z", "+00:00"))
        age_days = max(0.0, (datetime.now(timezone.utc) - published).total_seconds() / 86_400)
    except (TypeError, ValueError):
        return 0.35
    if age_days <= 1:
        return 1.0
    if age_days <= 7:
        return 0.85
    if age_days <= 30:
        return 0.70
    if age_days <= 365:
        return 0.50
    return 0.25


def _content_type_fit(source: Source) -> float:
    if not source.content_type:
        return 0.5
    normalized = source.content_type.lower()
    return 1.0 if normalized in {"text/html", "application/xhtml+xml", "text/plain", "application/pdf"} else 0.4


def rank(
    sources: list[Source],
    task_context: str,
    source_biases: dict[str, dict] | None = None,
    plugins: PluginRegistry | None = None,
    org_id: str = "development",
) -> list[RankedSource]:
    """Rank sources deterministically and retain low-scoring evidence for inspection."""
    domain_counts: dict[str, int] = {}
    for source in sources:
        host = urlparse(source.url).netloc.lower()
        domain_counts[host] = domain_counts.get(host, 0) + 1

    ranked: list[RankedSource] = []
    for source in sources:
        host = urlparse(source.url).netloc.lower()
        corroboration = min(1.0, (domain_counts[host] - 1) * 0.05)
        extraction_confidence = source.extraction_confidence if source.extraction_confidence is not None else 0.5
        score = (
            0.45 * source.trust_score
            + 0.25 * _relevance(source, task_context)
            + 0.10 * corroboration
            + 0.10 * _recency(source)
            + 0.05 * _content_type_fit(source)
            + 0.05 * max(0.0, min(1.0, extraction_confidence))
        )
        documentation_query = bool(re.search(r"\b(?:official|documentation|docs|reference|api|sdk|guide|framework)\b", task_context.lower()))
        hostname = urlparse(source.url).hostname.lower().rstrip(".") if urlparse(source.url).hostname else ""
        if documentation_query and (hostname in _OFFICIAL_DOCUMENTATION_HOSTS or any(hostname.endswith("." + host) for host in _OFFICIAL_DOCUMENTATION_HOSTS)):
            score += 0.15
        factual_query = bool(re.search(r"\b(?:capital|population|currency|flag)\b|\bwho is\b|\bwhat is\b", task_context.lower()))
        if factual_query:
            factual_text = f"{source.title} {source.snippet}"
            answer_bearing = bool(re.search(r"\b(?:capital|population|currency|flag)\b.{0,120}\b(?:is|was|are|equals|stands at)\b", factual_text, re.IGNORECASE))
            if answer_bearing:
                score += 0.18
            if source.content_type == "application/json":
                score += 0.05
            if urlparse(source.url).netloc.lower().endswith(("wikipedia.org", "wikidata.org", "restcountries.com")):
                score += 0.05
            if urlparse(source.url).netloc.lower() in {"github.com", "www.github.com"}:
                score -= 0.12
        bias = (source_biases or {}).get(source.id, {})
        haystack = f"{source.title} {source.snippet} {source.url}".lower()
        boosts = bias.get("boost", []) if isinstance(bias, dict) else []
        penalties = bias.get("penalize", []) if isinstance(bias, dict) else []
        score += min(0.15, 0.05 * sum(str(term).lower() in haystack for term in boosts))
        score -= min(0.15, 0.05 * sum(str(term).lower() in haystack for term in penalties))
        score = plugins.ranker_scores(org_id, source, task_context, score) if plugins is not None else score
        score = round(min(1.0, max(0.0, score)), 4)
        ranked.append(RankedSource(source=source, score=score, include=score >= 0.25))
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked
