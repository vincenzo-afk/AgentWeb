"""Phase 0/1 orchestration for grounded research and page monitoring."""

from __future__ import annotations

import os
import re
import time
import uuid
from urllib.parse import urlparse

from .alerting import send_webhook
from .browser import BrowserEngine
from .crawler import Crawler
from .fetch import extract_metadata, fetch_url, html_to_text, validate_url
from .memory import MemoryStore
from .models import Citation, Monitor, SolveResponse, Source, utc_now
from .normalizer import normalize
from .parser import parse
from .ranking import rank
from .scheduler import Scheduler
from .search import search
from .trace import Span, TraceStore
from .trust_engine import TrustEngine

URL_RE = re.compile(r"https?://[^\s)\]>]+")


class AgentWebEngine:
    def __init__(self, memory: MemoryStore | None = None) -> None:
        self.memory = memory or MemoryStore()
        self.traces = TraceStore(self.memory.path)
        self.trust_engine = TrustEngine(
            blocked_domains={domain for domain in os.getenv("AGENTWEB_BLOCKED_DOMAINS", "").split(",") if domain}
        )
        self.crawler = Crawler(self.trust_engine)
        self.browser = BrowserEngine(self.trust_engine)
        self.scheduler = Scheduler(self.memory, self.check_monitor)

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

    @staticmethod
    def _span(component: str, operation: str, started: float, status: str, input_summary: str, output_summary: str) -> Span:
        return Span(
            component=component,
            operation=operation,
            start_time=started,
            end_time=time.time(),
            status=status,
            input_summary=input_summary[:240],
            output_summary=output_summary[:240],
        )

    def _source_from_url(self, url: str) -> Source | None:
        decision = self.trust_engine.should_fetch(url)
        if not decision.allowed:
            return None
        result = fetch_url(url)
        if result.error and not result.body:
            return None
        parsed = parse(result.body.encode("utf-8"), result.content_type)
        title = parsed.title
        if not title:
            title, _ = extract_metadata(result.body)
        text = parsed.text or html_to_text(result.body)
        surface = self.trust_engine.should_surface(text)
        if not surface.allowed:
            return None
        return Source(
            id=self._source_id(url),
            url=result.url,
            title=title,
            snippet=text[:240],
            trust_score=self._trust_score(result.url, title),
        )

    def browser_open(self, url: str, actions: list[dict] | None = None, org_id: str = "development"):
        """Render a page through the isolated browser adapter and persist a trace."""
        started = time.time()
        execution_id = "exec_" + uuid.uuid4().hex[:16]
        try:
            session = self.browser.open(url, actions)
            self.traces.save(
                execution_id,
                [self._span("browser", "open", started, session.status, url, f"{len(session.actions)} action(s)")],
                                    status=session.status,
                    org_id=org_id,
                )

            return session
        except Exception as error:
            self.traces.save(
                execution_id,
                [self._span("browser", "open", started, "failed", url, str(error))],
                                    status="failed",
                    org_id=org_id,
                )

            raise

    def extract(self, url: str, requested_schema: dict | None = None) -> dict:
        validate_url(url)
        decision = self.trust_engine.should_fetch(url)
        if not decision.allowed:
            raise RuntimeError(decision.reason or "URL rejected by trust engine")
        result = fetch_url(url)
        if result.error:
            raise RuntimeError(f"could not fetch URL: {result.error}")
        parsed = parse(result.body.encode("utf-8"), result.content_type)
        title = parsed.title
        description = extract_metadata(result.body)[1]
        text = parsed.text or html_to_text(result.body)
        data = {
            "url": result.url,
            "status": result.status,
            "title": title,
            "description": description,
            "text": text,
            "links": parsed.links,
            "parse_warnings": parsed.parse_warnings,
            "trust_score": self._trust_score(result.url, title),
        }
        if requested_schema:
            structured: dict[str, dict] = {}
            for field, expected_type in requested_schema.items():
                candidate = title if field.lower() == "title" else text[:200]
                structured[field] = normalize(candidate, str(expected_type)).__dict__
            data["data"] = structured
        return data

    def solve(self, task: str, mode: str = "focus", org_id: str = "development") -> SolveResponse:
        task = task.strip()
        if not task or len(task) > 2000:
            raise ValueError("task must contain between 1 and 2000 characters")
        if mode not in {"flash", "focus", "dive"}:
            raise ValueError("mode must be one of: flash, focus, dive")

        execution_id = self.traces.start()
        spans: list[Span] = []
        started = time.time()
        requested_urls = list(dict.fromkeys(URL_RE.findall(task)))
        spans.append(self._span("planner", "classify", started, "complete", "task received", "direct URLs or search"))
        source_candidates: list[Source] = []
        for url in requested_urls[:5 if mode == "dive" else 3]:
            fetch_started = time.time()
            source = self._source_from_url(url)
            spans.append(
                self._span(
                    "extractor",
                    "fetch_and_parse",
                    fetch_started,
                    "complete" if source else "degraded",
                    url,
                    "source accepted" if source else "source unavailable or blocked",
                )
            )
            if source:
                source_candidates.append(source)

        if not source_candidates:
            search_started = time.time()
            search_results = search(task, limit=5 if mode in {"focus", "dive"} else 3)
            spans.append(self._span("search", "search", search_started, "complete", task, f"{len(search_results)} result(s)"))
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

        ranked = rank(source_candidates, task)
        spans.append(self._span("ranking", "rank_sources", time.time(), "complete", f"{len(source_candidates)} candidates", f"{len(ranked)} ranked"))
        limit = 1 if mode == "flash" else 3 if mode == "focus" else 5
        sources = [item.source for item in ranked if item.include][:limit]
        if sources:
            answer = (
                f"AgentWeb reviewed {len(sources)} source(s) for this task: {task}\n\n"
                + "\n".join(
                    f"{index}. {source.title or source.url} — {source.snippet[:280]}"
                    for index, source in enumerate(sources, start=1)
                )
            )
            citations = [Citation(claim_span=[0, len(answer)], source_ids=[source.id for source in sources])]
            insufficient = False
        else:
            answer = (
                f"No public sources were available for this task: {task}. "
                "Try a more specific query or provide a direct URL."
            )
            citations = []
            insufficient = True
        spans.append(self._span("synthesis", "synthesize", time.time(), "complete", task, f"{len(citations)} citation(s)"))
        self.traces.save(execution_id, spans, org_id=org_id)
        return SolveResponse(
            execution_id=execution_id,
            mode=mode,
            answer=answer,
            sources=sources,
            citations=citations,
            insufficient_evidence=insufficient,
        )

    def create_monitor(self, task: str, frequency: str = "hourly", webhook_url: str | None = None, org_id: str = "development") -> Monitor:
        task = task.strip()
        if not task or len(task) > 2000:
            raise ValueError("task must contain between 1 and 2000 characters")
        if frequency not in {"minutely", "hourly", "daily"}:
            raise ValueError("frequency must be one of: minutely, hourly, daily")
        target_url = next(iter(URL_RE.findall(task)), None)
        if webhook_url:
            validate_url(webhook_url)
        monitor = Monitor(
            id="mon_" + uuid.uuid4().hex[:16],
            task=task,
            frequency=frequency,
            target_url=target_url,
            webhook_url=webhook_url,
            org_id=org_id,
        )
        self.memory.create_monitor(monitor)
        self.traces.save(monitor.id, [self._span("monitor", "create", time.time(), "complete", task, monitor.id)], org_id=org_id)
        return monitor

    def check_monitor(self, monitor: Monitor) -> Monitor:
        if monitor.status != "active":
            return monitor
        now = utc_now()
        monitor.last_checked_at = now
        if not monitor.target_url:
            monitor.last_event = "check_failed"
            monitor.last_error = "monitor task does not include a direct URL"
            self.memory.update_monitor(monitor)
            self.traces.save(monitor.id, [self._span("monitor", "check", time.time(), monitor.last_event, monitor.task, monitor.last_error)], org_id=monitor.org_id)
            return monitor
        decision = self.trust_engine.should_fetch(monitor.target_url)
        if not decision.allowed:
            monitor.last_event = "check_failed"
            monitor.last_error = decision.reason
            self.memory.update_monitor(monitor)
            self.traces.save(monitor.id, [self._span("monitor", "check", time.time(), monitor.last_event, monitor.target_url, monitor.last_error)], org_id=monitor.org_id)
            return monitor
        result = fetch_url(monitor.target_url)
        if result.error:
            monitor.last_event = "check_failed"
            monitor.last_error = result.error
            self.memory.update_monitor(monitor)
            self.traces.save(monitor.id, [self._span("monitor", "check", time.time(), monitor.last_event, monitor.target_url, monitor.last_error)], org_id=monitor.org_id)
            return monitor
        monitor.last_error = None
        content = html_to_text(result.body)
        previous = self.memory.get_latest(monitor.target_url, monitor.org_id)
        changed = self.memory.save_snapshot(
            key=monitor.target_url,
            url=monitor.target_url,
            content=content,
            captured_at=now,
            org_id=monitor.org_id,
        )
        monitor.last_event = "change_detected" if changed else "no_change"
        if changed:
            monitor.last_change_at = now
            if monitor.webhook_url:
                secret = os.getenv("AGENTWEB_WEBHOOK_SIGNING_KEY", "")
                if not secret:
                    monitor.last_error = "webhook signing secret is not configured"
                else:
                    payload = {
                        "event": "monitor.change_detected",
                        "monitor_id": monitor.id,
                        "timestamp": now,
                        "diff": {
                            "target": monitor.target_url,
                            "from_hash": previous["content_hash"] if previous else None,
                            "to_hash": self.memory.get_latest(monitor.target_url, monitor.org_id)["content_hash"],
                        },
                    }
                    delivery = send_webhook(monitor.webhook_url, payload, secret)
                    if not delivery.delivered:
                        monitor.last_error = delivery.error or "webhook delivery failed"
        self.memory.update_monitor(monitor)
        self.traces.save(monitor.id, [self._span("monitor", "check", time.time(), monitor.last_event, monitor.target_url, monitor.last_event)], org_id=monitor.org_id)
        return monitor
