"""Network and HTML helpers for the free local MVP."""

from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .trust_engine import TrustEngine


MAX_BYTES = 2_000_000


@dataclass
class FetchResult:
    url: str
    status: int
    content_type: str
    body: str
    error: str | None = None


def validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be an absolute http or https URL")
    if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
        raise ValueError("URL credentials are not accepted")
    try:
        _ = parsed.port
    except ValueError as error:
        raise ValueError("URL port is invalid") from error
    return url


class _SafeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, trust_engine: TrustEngine) -> None:
        super().__init__()
        self.trust_engine = trust_engine

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urljoin(req.full_url, newurl)
        decision = self.trust_engine.should_fetch(target)
        if not decision.allowed:
            raise URLError(decision.reason or "redirect target rejected by trust engine")
        return super().redirect_request(req, fp, code, msg, headers, target)


def fetch_url(url: str, timeout: float = 10.0, trust_engine: TrustEngine | None = None, max_attempts: int = 3) -> FetchResult:
    validate_url(url)
    trust_engine = trust_engine or TrustEngine()
    decision = trust_engine.should_fetch(url)
    if not decision.allowed:
        raise ValueError(decision.reason or "URL rejected by trust engine")
    request = Request(
        url,
        headers={
            "User-Agent": "AgentWeb/0.1 (+https://github.com/vincenzo-afk/AgentWeb)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
        },
    )
    opener = build_opener(_SafeRedirectHandler(trust_engine))
    attempts = max(1, min(int(max_attempts), 3))
    last_error: Exception | None = None
    last_status = 0
    for attempt in range(1, attempts + 1):
        try:
            with opener.open(request, timeout=timeout) as response:
                final_decision = trust_engine.should_fetch(response.geturl())
                if not final_decision.allowed:
                    raise URLError(final_decision.reason or "final URL rejected by trust engine")
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raw = raw[:MAX_BYTES]
                charset = response.headers.get_content_charset() or "utf-8"
                return FetchResult(
                    url=response.geturl(),
                    status=response.status,
                    content_type=response.headers.get_content_type(),
                    body=raw.decode(charset, errors="replace"),
                )
        except HTTPError as error:
            last_error = error
            last_status = error.code
            retryable = error.code in {408, 425, 429, 500, 502, 503, 504}
            if not retryable or attempt >= attempts:
                break
            retry_after = error.headers.get("Retry-After") if error.headers else None
            try:
                delay = max(0.0, min(float(retry_after), 30.0)) if retry_after else min(0.5 * (2 ** (attempt - 1)), 30.0)
            except (TypeError, ValueError):
                delay = min(0.5 * (2 ** (attempt - 1)), 30.0)
            time.sleep(delay)
        except (URLError, TimeoutError, ValueError, OSError) as error:
            last_error = error
            if attempt >= attempts:
                break
            time.sleep(min(0.5 * (2 ** (attempt - 1)), 30.0))
    return FetchResult(url=url, status=last_status, content_type="", body="", error=str(last_error) if last_error else "fetch failed")


def html_to_text(source: str) -> str:
    without_blocks = re.sub(r"(?is)<(script|style|noscript|svg).*?>.*?</\1>", " ", source)
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_blocks)
    text = html.unescape(without_tags)
    return re.sub(r"\s+", " ", text).strip()


def extract_metadata(source: str) -> tuple[str, str]:
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", source)
    title = html_to_text(title_match.group(1)) if title_match else ""
    description_match = re.search(
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        source,
    )
    if not description_match:
        description_match = re.search(
            r'(?is)<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']',
            source,
        )
    description = html.unescape(description_match.group(1)).strip() if description_match else ""
    return title, description
