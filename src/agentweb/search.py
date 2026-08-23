"""Pluggable search providers with a free dependency-free fallback."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from urllib.request import Request, urlopen

from .fetch import html_to_text
from .secrets import SecretProvider, build_provider


class SearchProviderError(RuntimeError):
    """Raised when a configured search provider cannot return valid results."""


class SearchProvider(Protocol):
    def search(self, query: str, limit: int = 10, freshness: str | None = None) -> list[dict[str, str]]:
        ...


@dataclass(frozen=True)
class SearchProviderConfig:
    name: str = "duckduckgo"
    endpoint: str | None = None
    api_key_name: str = "AGENTWEB_SEARCH_API_KEY"
    timeout: float = 10.0

    @classmethod
    def from_environment(cls) -> "SearchProviderConfig":
        name = os.getenv("AGENTWEB_SEARCH_PROVIDER", "duckduckgo").strip().lower()
        if name not in {"duckduckgo", "json"}:
            raise SearchProviderError("AGENTWEB_SEARCH_PROVIDER must be duckduckgo or json")
        endpoint = os.getenv("AGENTWEB_SEARCH_ENDPOINT")
        try:
            timeout = max(1.0, min(float(os.getenv("AGENTWEB_SEARCH_TIMEOUT_SECONDS", "10")), 30.0))
        except ValueError as error:
            raise SearchProviderError("AGENTWEB_SEARCH_TIMEOUT_SECONDS must be numeric") from error
        if name == "json" and not endpoint:
            raise SearchProviderError("AGENTWEB_SEARCH_ENDPOINT is required for the json provider")
        return cls(name=name, endpoint=endpoint, timeout=timeout)


def _clean_result_url(href: str) -> str:
    parsed = urlparse(href)
    if parsed.path == "/l/":
        query = parse_qs(parsed.query)
        if query.get("uddg"):
            return unquote(query["uddg"][0])
    return href


def _validate_query(query: str, limit: int, freshness: str | None) -> tuple[str, int, str | None]:
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")
    try:
        limit = max(1, min(int(limit), 50))
    except (TypeError, ValueError) as error:
        raise ValueError("limit must be an integer") from error
    if freshness is not None and freshness not in {"day", "week", "month", "year", "any"}:
        raise ValueError("freshness must be one of: day, week, month, year, any")
    return query, limit, freshness


class DuckDuckGoHTMLProvider:
    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def search(self, query: str, limit: int = 10, freshness: str | None = None) -> list[dict[str, str]]:
        query, limit, freshness = _validate_query(query, limit, freshness)
        params = {"q": query}
        if freshness and freshness != "any":
            params["df"] = {"day": "d", "week": "w", "month": "m", "year": "y"}[freshness]
        endpoint = "https://html.duckduckgo.com/html/?" + urlencode(params)
        request = Request(endpoint, headers={"User-Agent": "AgentWeb/0.5"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read(1_500_000).decode("utf-8", errors="replace")
        except Exception as error:
            raise SearchProviderError(f"DuckDuckGo provider unavailable: {type(error).__name__}") from error

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


class JsonSearchProvider:
    """Provider for a licensed or self-hosted JSON search endpoint.

    The endpoint receives ``q``, ``limit``, and optional ``freshness`` query
    parameters and returns ``{"results": [{"url", "title", "snippet"}]}``.
    """

    def __init__(self, endpoint: str, api_key: str | None = None, timeout: float = 10.0) -> None:
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SearchProviderError("AGENTWEB_SEARCH_ENDPOINT must be an HTTP(S) URL")
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout

    def search(self, query: str, limit: int = 10, freshness: str | None = None) -> list[dict[str, str]]:
        query, limit, freshness = _validate_query(query, limit, freshness)
        params = {"q": query, "limit": str(limit)}
        if freshness:
            params["freshness"] = freshness
        separator = "&" if "?" in self.endpoint else "?"
        request = Request(self.endpoint + separator + urlencode(params), headers={"Accept": "application/json", "User-Agent": "AgentWeb/0.5"})
        if self.api_key:
            request.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read(2_000_000).decode("utf-8"))
        except Exception as error:
            raise SearchProviderError(f"JSON search provider unavailable: {type(error).__name__}") from error
        raw_results = payload.get("results") if isinstance(payload, dict) else payload
        if not isinstance(raw_results, list):
            raise SearchProviderError("JSON search provider returned an invalid result list")
        results: list[dict[str, str]] = []
        for item in raw_results[:limit]:
            if not isinstance(item, dict) or not isinstance(item.get("url"), str):
                continue
            url = item["url"]
            if not url.startswith(("http://", "https://")):
                continue
            result = {
                "url": url,
                "title": str(item.get("title", "")),
                "snippet": str(item.get("snippet", item.get("description", ""))),
            }
            if item.get("published_at"):
                result["published_at"] = str(item["published_at"])
            results.append(result)
        return results


class FallbackSearchProvider:
    def __init__(self, primary: SearchProvider, fallback: SearchProvider | None = None) -> None:
        self.primary = primary
        self.fallback = fallback or DuckDuckGoHTMLProvider()

    def search(self, query: str, limit: int = 10, freshness: str | None = None) -> list[dict[str, str]]:
        try:
            return self.primary.search(query, limit, freshness)
        except SearchProviderError:
            if isinstance(self.primary, DuckDuckGoHTMLProvider):
                return []
            try:
                return self.fallback.search(query, limit, freshness)
            except SearchProviderError:
                return []


def build_search_provider(secret_provider: SecretProvider | None = None) -> SearchProvider:
    config = SearchProviderConfig.from_environment()
    if config.name == "duckduckgo":
        return DuckDuckGoHTMLProvider(config.timeout)
    secret_provider = secret_provider or build_provider()
    api_key = secret_provider.get(config.api_key_name, required=False)
    return FallbackSearchProvider(JsonSearchProvider(config.endpoint or "", api_key, config.timeout))


def search(query: str, limit: int = 10, freshness: str | None = None, provider: SearchProvider | None = None) -> list[dict[str, str]]:
    """Return normalized provider results, falling back to the free local adapter."""
    if provider is None:
        provider = build_search_provider()
    return provider.search(query, limit, freshness)
