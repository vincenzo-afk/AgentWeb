"""Deterministic source ranking for the Phase 0/1 evidence pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from .models import Source


@dataclass
class RankedSource:
    source: Source
    score: float
    include: bool = True


def _relevance(source: Source, task_context: str) -> float:
    terms = {term.lower() for term in task_context.split() if len(term) > 3}
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


def rank(sources: list[Source], task_context: str, source_biases: dict[str, dict] | None = None) -> list[RankedSource]:
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
        bias = (source_biases or {}).get(source.id, {})
        haystack = f"{source.title} {source.snippet} {source.url}".lower()
        boosts = bias.get("boost", []) if isinstance(bias, dict) else []
        penalties = bias.get("penalize", []) if isinstance(bias, dict) else []
        score += min(0.15, 0.05 * sum(str(term).lower() in haystack for term in boosts))
        score -= min(0.15, 0.05 * sum(str(term).lower() in haystack for term in penalties))
        score = round(min(1.0, max(0.0, score)), 4)
        ranked.append(RankedSource(source=source, score=score, include=score >= 0.25))
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked
