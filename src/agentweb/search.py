"""Search adapter for the local MVP.

The adapter deliberately keeps the provider boundary small so a deployment can
replace it with a licensed provider without changing the API contract.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from urllib.request import Request, urlopen

from .fetch import html_to_text


def _clean_result_url(href: str) -> str:
    parsed = urlparse(href)
    if parsed.path == "/l/":
        query = parse_qs(parsed.query)
        if query.get("uddg"):
            return unquote(query["uddg"][0])
    return href


def search(query: str, limit: int = 10, timeout: float = 10.0) -> list[dict[str, str]]:
    """Return public search results, or an empty list if the provider is unavailable."""
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")
    limit = max(1, min(int(limit), 25))
    endpoint = "https://html.duckduckgo.com/html/?" + urlencode({"q": query})
    request = Request(endpoint, headers={"User-Agent": "AgentWeb/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(1_500_000).decode("utf-8", errors="replace")
    except Exception:
        return []

    results: list[dict[str, str]] = []
    pattern = re.compile(
        r'(?is)<a[^>]+class=["\'][^"\']*result__a[^"\']*["\'][^>]+href=["\'](.*?)["\'][^>]*>(.*?)</a>'
    )
    for href, title_markup in pattern.findall(body):
        url = _clean_result_url(href)
        title = html_to_text(title_markup)
        if not url.startswith(("http://", "https://")):
            continue
        snippet_match = re.search(
            r'(?is)<a[^>]+class=["\'][^"\']*result__a[^"\']*["\'][\s\S]*?'
            r'<a[^>]+class=["\'][^"\']*result__snippet[^"\']*["\'][^>]*>(.*?)</a>',
            body[body.find(title_markup) :],
        )
        snippet = html_to_text(snippet_match.group(1)) if snippet_match else ""
        results.append({"url": url, "title": title, "snippet": snippet})
        if len(results) >= limit:
            break
    return results
