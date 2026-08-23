"""Bounded breadth-first crawling built on the fetch and parser adapters."""

from __future__ import annotations

import re
import urllib.robotparser
from urllib.error import HTTPError
from collections import deque
from dataclasses import asdict, dataclass
from urllib.parse import urldefrag, urljoin, urlparse

from .fetch import fetch_url
from .parser import parse
from .trust_engine import TrustEngine


@dataclass
class CrawledPage:
    url: str
    status: int
    extracted: bool
    depth: int
    error: str | None = None


@dataclass
class CrawlResult:
    pages: list[CrawledPage]
    pages_crawled: int
    truncated: bool

    def to_dict(self) -> dict:
        return {
            "pages": [asdict(page) for page in self.pages],
            "pages_crawled": self.pages_crawled,
            "truncated": self.truncated,
        }


class Crawler:
    def __init__(self, trust_engine: TrustEngine | None = None, user_agent: str = "AgentWeb/0.2") -> None:
        self.trust_engine = trust_engine or TrustEngine()
        self.user_agent = user_agent
        self._robots: dict[str, urllib.robotparser.RobotFileParser | bool] = {}

    def _allowed_by_robots(self, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots:
            parser = urllib.robotparser.RobotFileParser(f"{origin}/robots.txt")
            try:
                parser.read()
                self._robots[origin] = parser
            except HTTPError as error:
                # A missing robots file is equivalent to no published policy;
                # other HTTP failures fail closed to avoid bypassing policy.
                self._robots[origin] = error.code == 404
            except Exception:
                self._robots[origin] = False
        parser = self._robots[origin]
        return parser if isinstance(parser, bool) else parser.can_fetch(self.user_agent, url)

    def crawl(
        self,
        start_url: str,
        max_pages: int = 50,
        depth: int = 2,
        url_pattern: str | None = None,
    ) -> CrawlResult:
        decision = self.trust_engine.should_fetch(start_url)
        if not decision.allowed:
            raise ValueError(decision.reason or "start URL rejected by trust engine")
        max_pages = max(1, min(int(max_pages), 50))
        depth = max(0, min(int(depth), 10))
        pattern = re.compile(url_pattern) if url_pattern else None
        queue: deque[tuple[str, int]] = deque([(start_url, 0)])
        seen: set[str] = set()
        pages: list[CrawledPage] = []
        truncated = False
        while queue and len(pages) < max_pages:
            url, current_depth = queue.popleft()
            url = urldefrag(url)[0]
            if url in seen:
                continue
            seen.add(url)
            if pattern and not pattern.search(url):
                continue
            if not self._allowed_by_robots(url):
                pages.append(CrawledPage(url, 0, False, current_depth, "blocked by robots.txt"))
                continue
            result = fetch_url(url, trust_engine=self.trust_engine)
            if result.error:
                pages.append(CrawledPage(url, result.status, False, current_depth, result.error))
                continue
            parsed = parse(result.body.encode("utf-8"), result.content_type)
            pages.append(CrawledPage(result.url, result.status, True, current_depth))
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
        return CrawlResult(pages=pages, pages_crawled=len(pages), truncated=truncated)
