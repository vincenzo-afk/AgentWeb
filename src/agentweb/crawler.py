from __future__ import annotations

import os
import re
import threading
import time
import urllib.robotparser
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urldefrag, urljoin, urlparse

from .errors import RateLimitError
from .fetch import fetch_url
from .memory import MemoryStore
from .parser import ParsedDocument, parse
from .redaction import redact_text
from .trust_engine import TrustEngine


@dataclass
class CrawledPage:
    url: str
    status: int
    extracted: bool
    depth: int
    error: str | None = None
    content_hash: str | None = None
    content_type: str | None = None
    title: str | None = None
    parse_warnings: list[str] = field(default_factory=list)


@dataclass
class CrawlResult:
    pages: list[CrawledPage]
    pages_crawled: int
    truncated: bool
    crawl_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "crawl_id": self.crawl_id,
            "pages": [asdict(page) for page in self.pages],
            "pages_crawled": self.pages_crawled,
            "truncated": self.truncated,
        }


class Crawler:
    """Run bounded same-origin breadth-first crawls with durable local history."""

    def __init__(
        self,
        trust_engine: TrustEngine | None = None,
        user_agent: str = "AgentWeb/0.2",
        rate_limit_interval: float | None = None,
        *,
        memory: MemoryStore | None = None,
        coordinator: Any | None = None,
        shared_capacity: float = 60.0,
        shared_refill_per_second: float = 1.0,
    ) -> None:
        self.trust_engine = trust_engine or TrustEngine()
        self.user_agent = user_agent
        self.memory = memory
        self.coordinator = coordinator
        configured_interval = os.getenv("AGENTWEB_CRAWL_MIN_INTERVAL_SECONDS", "0.1")
        try:
            interval = float(configured_interval) if rate_limit_interval is None else float(rate_limit_interval)
        except (TypeError, ValueError):
            interval = 0.1
        self.rate_limit_interval = max(0.0, interval)
        self.shared_capacity = max(1.0, float(shared_capacity))
        self.shared_refill_per_second = max(0.0, float(shared_refill_per_second))
        self._last_request_at: dict[str, float] = {}
        self._rate_lock = threading.Lock()
        self._robots: dict[str, urllib.robotparser.RobotFileParser | bool] = {}
        self._robots_lock = threading.Lock()

    def _allowed_by_robots(self, url: str, org_id: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        with self._robots_lock:
            cached = self._robots.get(origin)
        if cached is None:
            robots_url = f"{origin}/robots.txt"
            self._respect_rate_limit(robots_url, org_id)
            parser = urllib.robotparser.RobotFileParser(robots_url)
            try:
                parser.read()
                cached = parser
            except HTTPError as error:
                # A missing robots file is equivalent to no published policy;
                # other HTTP failures fail closed to avoid bypassing policy.
                cached = error.code == 404
            except Exception:
                cached = False
            with self._robots_lock:
                self._robots[origin] = cached
        return cached if isinstance(cached, bool) else cached.can_fetch(self.user_agent, url)

    def _respect_rate_limit(self, url: str, org_id: str) -> None:
        host = urlparse(url).netloc.lower()
        if self.coordinator is not None:
            self.coordinator.consume_rate_limit(
                org_id,
                f"crawl:{host}",
                1.0,
                self.shared_capacity,
                self.shared_refill_per_second,
            )
        if self.rate_limit_interval <= 0:
            return
        with self._rate_lock:
            now = time.monotonic()
            previous = self._last_request_at.get(host)
            if previous is not None:
                time.sleep(max(0.0, previous + self.rate_limit_interval - now))
            self._last_request_at[host] = time.monotonic()

    @staticmethod
    def _projection(parsed: ParsedDocument, content: str) -> dict[str, object]:
        return {
            "title": parsed.title,
            "text": content,
            "links": list(parsed.links[:100]),
            "tables": [table[:20] for table in parsed.tables[:10]],
            "entities": list(parsed.entities[:50]),
            "data": parsed.data,
        }

    @staticmethod
    def _captured_at() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _record_page(
        self,
        crawl_id: str,
        org_id: str,
        page: CrawledPage,
        *,
        content: str | None = None,
        parsed: ParsedDocument | None = None,
    ) -> None:
        if self.memory is None:
            return
        if content is not None and parsed is not None:
            snapshot = self.memory.snapshot(
                page.url,
                content,
                self._captured_at(),
                org_id,
                self._projection(parsed, content),
            )
            page.content_hash = snapshot["content_hash"]
        self.memory.save_crawl_page(crawl_id, org_id, asdict(page))

    def crawl(
        self,
        start_url: str,
        max_pages: int = 50,
        depth: int = 2,
        url_pattern: str | None = None,
        org_id: str = "development",
    ) -> CrawlResult:
        decision = self.trust_engine.should_fetch(start_url)
        if not decision.allowed:
            raise ValueError(decision.reason or "start URL rejected by trust engine")
        max_pages = max(1, min(int(max_pages), 50))
        depth = max(0, min(int(depth), 10))
        pattern = re.compile(url_pattern) if url_pattern else None
        crawl_id = "crawl_" + uuid.uuid4().hex[:16]
        if self.memory is not None:
            self.memory.create_crawl(crawl_id, org_id, start_url, max_pages, depth, url_pattern)
        queue: deque[tuple[str, int]] = deque([(start_url, 0)])
        seen: set[str] = set()
        pages: list[CrawledPage] = []
        truncated = False
        status = "completed"
        try:
            while queue and len(pages) < max_pages:
                url, current_depth = queue.popleft()
                url = urldefrag(url)[0]
                if url in seen:
                    continue
                seen.add(url)
                if pattern and not pattern.search(url):
                    continue
                if not self._allowed_by_robots(url, org_id):
                    page = CrawledPage(url, 0, False, current_depth, "blocked by robots.txt")
                    pages.append(page)
                    self._record_page(crawl_id, org_id, page)
                    continue
                self._respect_rate_limit(url, org_id)
                result = fetch_url(url, trust_engine=self.trust_engine)
                if result.error:
                    page = CrawledPage(url, result.status, False, current_depth, redact_text(result.error))
                    pages.append(page)
                    self._record_page(crawl_id, org_id, page)
                    continue
                parsed = parse(result.body.encode("utf-8"), result.content_type)
                content = parsed.text or result.body
                page = CrawledPage(
                    result.url,
                    result.status,
                    True,
                    current_depth,
                    content_type=parsed.content_type,
                    title=parsed.title or None,
                    parse_warnings=list(parsed.parse_warnings),
                )
                pages.append(page)
                self._record_page(crawl_id, org_id, page, content=content, parsed=parsed)
                if current_depth >= depth:
                    continue
                for link in parsed.links:
                    child = urldefrag(urljoin(result.url, link))[0]
                    child_parsed = urlparse(child)
                    if child_parsed.scheme in {"http", "https"} and child_parsed.netloc == urlparse(start_url).netloc:
                        if child not in seen:
                            queue.append((child, current_depth + 1))
            if queue:
                truncated = True
            return CrawlResult(pages=pages, pages_crawled=len(pages), truncated=truncated, crawl_id=crawl_id)
        except RateLimitError:
            status = "rate_limited"
            raise
        except Exception:
            status = "failed"
            raise
        finally:
            if self.memory is not None:
                self.memory.complete_crawl(crawl_id, org_id, len(pages), truncated, status)
