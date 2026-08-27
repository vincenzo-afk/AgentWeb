"""Adaptive research policy and evidence gates.

The policy is deliberately deterministic and bounded. It decides whether to
continue searching from the evidence already collected, rather than running
every branch on every request. Optional model-assisted suggestions are applied
only when a configured model router is available.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlparse


@dataclass(frozen=True)
class ResearchPolicy:
    mode: str
    max_rounds: int
    max_queries: int
    max_candidates: int
    target_sources: int
    min_evidence_score: float
    max_seconds: float
    max_concurrency: int

    @classmethod
    def for_mode(cls, mode: str, *, max_rounds: int | None = None, max_concurrency: int | None = None) -> "ResearchPolicy":
        defaults = {
            "flash": (2, 4, 24, 2, 0.45, 35.0, 4),
            "focus": (3, 8, 60, 5, 0.58, 75.0, 6),
            "dive": (5, 14, 120, 8, 0.66, 120.0, 8),
            "monitor": (3, 8, 60, 5, 0.55, 75.0, 6),
        }
        rounds, queries, candidates, targets, score, seconds, concurrency = defaults.get(mode, defaults["focus"])
        return cls(
            mode=mode,
            max_rounds=max(1, min(int(max_rounds or rounds), 6)),
            max_queries= max(1, min(queries, 20)),
            max_candidates=max(4, min(candidates, 150)),
            target_sources=max(1, min(targets, 12)),
            min_evidence_score=max(0.0, min(score, 0.99)),
            max_seconds=max(5.0, min(seconds, 180.0)),
            max_concurrency=max(1, min(int(max_concurrency or concurrency), 8)),
        )


def source_family(url: str) -> str:
    host = urlparse(url).netloc.lower().split(":", 1)[0]
    if "wikipedia" in host or "wikidata" in host or "dbpedia" in host:
        return "knowledge"
    if "github" in host or "stackoverflow" in host or "stackexchange" in host:
        return "technical"
    if "arxiv" in host or "openalex" in host or "semanticscholar" in host or "pubmed" in host or "openreview" in host or host.endswith(".edu"):
        return "academic"
    if "reddit" in host or "news.ycombinator" in host:
        return "discussion"
    if "youtube" in host or "youtu.be" in host or "vimeo" in host:
        return "media"
    if "web.archive.org" in host:
        return "archive"
    return "web"


def evidence_state(task: str, sources: list[object]) -> dict[str, object]:
    urls = [str(getattr(source, "url", "")) for source in sources]
    families = {source_family(url) for url in urls if url}
    hosts = {urlparse(url).netloc.lower().split(":", 1)[0] for url in urls if urlparse(url).netloc}
    lowered = task.lower()
    required: set[str] = set()
    if re.search(r"\b(?:paper|academic|study|research|citation)\b", lowered):
        required.add("academic")
    if re.search(r"\b(?:code|github|api|library|implementation|technical)\b", lowered):
        required.add("technical")
    if re.search(r"\b(?:video|youtube|watch|transcript)\b", lowered):
        required.add("media")
    comparison_official = bool(re.search(r"\b(?:compare|comparison|frameworks?)\b", lowered) and re.search(r"\b(?:official|documentation|docs|release|changelog)\b", lowered))
    if re.search(r"\b(?:latest|current|today|news|trend)\b", lowered):
        required.add("web")
        if not comparison_official:
            required.add("discussion")
    if re.search(r"\b(?:capital|population|currency)\b|\bwho is\b|\bwhat is\b", lowered):
        required.add("knowledge")
    missing = sorted(required - families)
    authority = sum(1 for source in sources if float(getattr(source, "trust_score", 0.0) or 0.0) >= 0.75)
    populated = sum(1 for source in sources if str(getattr(source, "snippet", "") or getattr(source, "title", "")).strip())
    score = min(1.0, 0.25 * min(len(families), 4) / 4 + 0.25 * min(len(hosts), 6) / 6 + 0.25 * min(authority, 4) / 4 + 0.25 * min(populated, 8) / 8)
    return {"source_count": len(sources), "source_families": sorted(families), "host_count": len(hosts), "required_families": sorted(required), "missing_families": missing, "authority_count": authority, "populated_count": populated, "score": round(score, 2)}


def follow_up_queries(task: str, state: dict[str, object], round_number: int) -> list[str]:
    missing = [str(item) for item in state.get("missing_families", [])]
    queries: list[str] = []
    if "knowledge" in missing:
        queries.append(f"{task} official facts and encyclopedia record")
    if "academic" in missing:
        queries.append(f"{task} peer reviewed study primary research")
    if "technical" in missing:
        queries.append(f"{task} official documentation implementation repository")
    if "media" in missing:
        queries.append(f"{task} video transcript official channel")
    if "discussion" in missing:
        queries.append(f"{task} expert discussion counterevidence")
    if not queries:
        queries = [
            f"{task} primary sources official documentation",
            f"{task} independent analysis evidence limitations",
        ]
    if round_number > 1:
        queries = [f"{query} round {round_number}" for query in queries]
    return list(dict.fromkeys(queries))[:4]


def should_continue(policy: ResearchPolicy, state: dict[str, object], *, round_number: int, elapsed_seconds: float, tried_queries: int) -> tuple[bool, str]:
    if elapsed_seconds >= policy.max_seconds:
        return False, "wall_clock_budget_reached"
    if round_number >= policy.max_rounds:
        return False, "max_rounds_reached"
    if tried_queries >= policy.max_queries:
        return False, "query_budget_reached"
    if int(state.get("source_count", 0)) >= policy.target_sources and not state.get("missing_families") and float(state.get("score", 0.0)) >= policy.min_evidence_score:
        return False, "evidence_gate_satisfied"
    if int(state.get("source_count", 0)) >= policy.max_candidates:
        return False, "candidate_budget_reached"
    return True, "evidence_gap_remains"
