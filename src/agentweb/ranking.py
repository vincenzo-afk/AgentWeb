"""Deterministic source ranking for the Phase 0/1 evidence pipeline."""

from __future__ import annotations

from dataclasses import dataclass
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


def rank(sources: list[Source], task_context: str) -> list[RankedSource]:
    """Rank sources deterministically and retain low-scoring evidence for inspection."""
    domain_counts: dict[str, int] = {}
    for source in sources:
        host = urlparse(source.url).netloc.lower()
        domain_counts[host] = domain_counts.get(host, 0) + 1

    ranked: list[RankedSource] = []
    for source in sources:
        host = urlparse(source.url).netloc.lower()
        corroboration = min(1.0, (domain_counts[host] - 1) * 0.05)
        score = round(
            min(1.0, 0.60 * source.trust_score + 0.35 * _relevance(source, task_context) + corroboration),
            4,
        )
        ranked.append(RankedSource(source=source, score=score, include=score >= 0.25))
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked
