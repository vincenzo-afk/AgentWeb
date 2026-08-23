"""Network and HTML helpers for the free local MVP."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


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
    return url


def fetch_url(url: str, timeout: float = 10.0) -> FetchResult:
    validate_url(url)
    request = Request(
        url,
        headers={
            "User-Agent": "AgentWeb/0.1 (+https://github.com/vincenzo-afk/AgentWeb)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
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
        return FetchResult(url=url, status=error.code, content_type="", body="", error=str(error))
    except (URLError, TimeoutError, ValueError, OSError) as error:
        return FetchResult(url=url, status=0, content_type="", body="", error=str(error))


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
