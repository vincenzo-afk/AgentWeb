"""Phase 0 orchestration for grounded research and page monitoring."""

from __future__ import annotations

import re
import uuid
from urllib.parse import urlparse

from .fetch import extract_metadata, fetch_url, html_to_text
from .memory import MemoryStore
from .models import Citation, Monitor, SolveResponse, Source, utc_now
from .search import search

URL_RE = re.compile(r"https?://[^\s)\]>]+")


class AgentWebEngine:
    def __init__(self, memory: MemoryStore | None = None) -> None:
        self.memory = memory or MemoryStore()

    @staticmethod
    def _trust_score(url: str, title: str = "") -> float:
        host = urlparse(url).netloc.lower().split(":", 1)[0]
        score = 0.55
        if host.endswith(".gov") or host.endswith(".edu"):
            score += 0.30
        elif host.endswith(".org"):
            score += 0.10
        if title:
            score += 0.05
        if url.startswith("https://"):
            score += 0.05
        return round(min(score, 0.99), 2)

    @staticmethod
    def _source_id(url: str) -> str:
        return "src_" + uuid.uuid5(uuid.NAMESPACE_URL, url).hex[:12]

    def _source_from_url(self, url: str) -> Source | None:
        result = fetch_url(url)
        if result.error and not result.body:
            return None
        title, description = extract_metadata(result.body)
        text = html_to_text(result.body)
        return Source(
            id=self._source_id(url),
            url=result.url,
            title=title,
            snippet=description or text[:240],
            trust_score=self._trust_score(result.url, title),
        )

    def extract(self, url: str, requested_schema: dict | None = None) -> dict:
        result = fetch_url(url)
        if result.error:
            raise RuntimeError(f"could not fetch URL: {result.error}")
        title, description = extract_metadata(result.body)
        text = html_to_text(result.body)
        data = {
            "url": result.url,
            "status": result.status,
            "title": title,
            "description": description,
            "text": text,
            "trust_score": self._trust_score(result.url, title),
        }
        if requested_schema:
            data["requested_schema"] = requested_schema
        return data

    def solve(self, task: str, mode: str = "focus") -> SolveResponse:
        task = task.strip()
        if not task:
            raise ValueError("task must not be empty")
        if mode not in {"flash", "focus", "dive", "monitor"}:
            raise ValueError("mode must be one of: flash, focus, dive, monitor")

        requested_urls = list(dict.fromkeys(URL_RE.findall(task)))
        source_candidates: list[Source] = []
        for url in requested_urls[:5 if mode == "dive" else 3]:
            source = self._source_from_url(url)
            if source:
                source_candidates.append(source)

        if not source_candidates:
            search_results = search(task, limit=5 if mode in {"focus", "dive"} else 3)
            for item in search_results:
                source_candidates.append(
                    Source(
                        id=self._source_id(item["url"]),
                        url=item["url"],
                        title=item.get("title", ""),
                        snippet=item.get("snippet", ""),
                        trust_score=self._trust_score(item["url"], item.get("title", "")),
                    )
                )

        source_candidates.sort(key=lambda source: source.trust_score, reverse=True)
        sources = source_candidates[: (1 if mode == "flash" else 3 if mode == "focus" else 5)]
        if sources:
            answer = (
                f"AgentWeb reviewed {len(sources)} source(s) for this task: {task}\n\n"
                + "\n".join(
                    f"{index}. {source.title or source.url} — {source.snippet[:280]}"
                    for index, source in enumerate(sources, start=1)
                )
            )
            citations = [Citation(claim_span=[0, len(answer)], source_ids=[source.id for source in sources])]
        else:
            answer = (
                f"No public sources were available for this task: {task}. "
                "Try a more specific query or provide a direct URL."
            )
            citations = []
        return SolveResponse(
            execution_id="exec_" + uuid.uuid4().hex[:16],
            mode=mode,
            answer=answer,
            sources=sources,
            citations=citations,
        )

    def create_monitor(self, task: str, frequency: str = "daily") -> Monitor:
        task = task.strip()
        if not task:
            raise ValueError("task must not be empty")
        if frequency not in {"minutely", "hourly", "daily"}:
            raise ValueError("frequency must be one of: minutely, hourly, daily")
        target_url = next(iter(URL_RE.findall(task)), None)
        monitor = Monitor(
            id="mon_" + uuid.uuid4().hex[:16],
            task=task,
            frequency=frequency,
            target_url=target_url,
        )
        self.memory.create_monitor(monitor)
        return monitor

    def check_monitor(self, monitor: Monitor) -> Monitor:
        if monitor.status != "active":
            return monitor
        now = utc_now()
        monitor.last_checked_at = now
        if not monitor.target_url:
            monitor.last_error = "monitor task does not include a direct URL"
            self.memory.update_monitor(monitor)
            return monitor
        result = fetch_url(monitor.target_url)
        if result.error:
            monitor.last_error = result.error
            self.memory.update_monitor(monitor)
            return monitor
        monitor.last_error = None
        changed = self.memory.save_snapshot(
            key=f"monitor:{monitor.id}",
            url=monitor.target_url,
            content=html_to_text(result.body),
            captured_at=now,
        )
        if changed:
            monitor.last_change_at = now
        self.memory.update_monitor(monitor)
        return monitor
