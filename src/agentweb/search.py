"""Pluggable search providers with a free dependency-free fallback."""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from html.parser import HTMLParser
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

        lowered_body = body.lower()
        if "anomaly.js" in lowered_body or "bots use duckduckgo too" in lowered_body:
            raise SearchProviderError("DuckDuckGo provider blocked the automated request")

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


class _BraveResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.snippet_depth: int | None = None
        self.current_link: str | None = None
        self.current_link_depth: int | None = None
        self.link_parts: list[str] = []
        self.body_parts: list[str] = []
        self.links: list[tuple[str, str, str]] = []
        self._link_seen = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "div" and "snippet" in classes and self.snippet_depth is None:
            self.snippet_depth = self.depth
            self.link_parts = []
            self.body_parts = []
            self._link_seen = False
        elif tag == "a" and self.snippet_depth is not None and not self._link_seen:
            href = attributes.get("href") or ""
            if href.startswith(("http://", "https://")) and "search.brave.com" not in href and "imgs.search.brave.com" not in href:
                self.current_link = href
                self.current_link_depth = self.depth
                self.link_parts = []
                self._link_seen = True
        self.depth += 1

    def handle_data(self, data: str) -> None:
        if self.snippet_depth is None:
            return
        text = " ".join(data.split())
        if not text:
            return
        self.body_parts.append(text)
        if self.current_link is not None:
            self.link_parts.append(text)

    def handle_endtag(self, tag: str) -> None:
        self.depth = max(0, self.depth - 1)
        if tag == "a" and self.current_link is not None and self.current_link_depth == self.depth:
            self.links.append((self.current_link, " ".join(self.link_parts).strip(), " ".join(self.body_parts).strip()))
            self.current_link = None
            self.current_link_depth = None
        if tag == "div" and self.snippet_depth is not None and self.depth == self.snippet_depth:
            self.snippet_depth = None


class BraveSearchHTMLProvider:
    """General public web discovery through Brave's HTML search page."""

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def search(self, query: str, limit: int = 10, freshness: str | None = None) -> list[dict[str, str]]:
        query, limit, _ = _validate_query(query, limit, freshness)
        endpoint = "https://search.brave.com/search?" + urlencode({"q": query})
        request = Request(endpoint, headers={"User-Agent": "Mozilla/5.0 (compatible; AgentWeb/0.13)", "Accept": "text/html,application/xhtml+xml"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read(2_000_000).decode("utf-8", errors="replace")
        except Exception as error:
            raise SearchProviderError(f"Brave provider unavailable: {type(error).__name__}") from error
        parser = _BraveResultParser()
        parser.feed(body)
        results: list[dict[str, str]] = []
        seen: set[str] = set()
        for url, title, raw_body in parser.links:
            if url in seen:
                continue
            seen.add(url)
            snippet = raw_body
            if title and snippet.startswith(title):
                snippet = snippet[len(title):].strip(" -:")
            results.append({"url": url, "title": title or url, "snippet": snippet[:1_000]})
            if len(results) >= limit:
                break
        return results


def _clean_bing_result_url(href: str) -> str:
    parsed = urlparse(href)
    encoded = parse_qs(parsed.query).get("u", [""])[0]
    if encoded.startswith("a1"):
        try:
            raw = encoded[2:]
            raw += "=" * (-len(raw) % 4)
            decoded = base64.urlsafe_b64decode(raw).decode("utf-8", errors="ignore")
            if decoded.startswith(("http://", "https://")):
                return decoded
        except Exception:
            pass
    return href


class BingSearchHTMLProvider:
    """General public web discovery through Bing's HTML result page."""

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def search(self, query: str, limit: int = 10, freshness: str | None = None) -> list[dict[str, str]]:
        query, limit, _ = _validate_query(query, limit, freshness)
        endpoint = "https://www.bing.com/search?" + urlencode({"q": query})
        request = Request(endpoint, headers={"User-Agent": "Mozilla/5.0 (compatible; AgentWeb/0.13)", "Accept": "text/html,application/xhtml+xml"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read(2_000_000).decode("utf-8", errors="replace")
        except Exception as error:
            raise SearchProviderError(f"Bing provider unavailable: {type(error).__name__}") from error
        results: list[dict[str, str]] = []
        seen: set[str] = set()
        pattern = re.compile(r'(?is)<li[^>]*class=["\'][^"\']*\bb_algo\b[^"\']*["\'][^>]*>.*?<h2[^>]*>.*?<a[^>]*href=["\'](.*?)["\'][^>]*>(.*?)</a>.*?<p[^>]*>(.*?)</p>')
        for href, title_markup, snippet_markup in pattern.findall(body):
            url = _clean_bing_result_url(html_to_text(href))
            if not url.startswith(("http://", "https://")) or "bing.com/ck/a" in url or url in seen:
                continue
            seen.add(url)
            results.append({"url": url, "title": html_to_text(title_markup), "snippet": html_to_text(snippet_markup)[:1_000]})
            if len(results) >= limit:
                break
        return results


class GitHubRepositorySearchProvider:
    """Bounded public-repository search branch for technical queries."""

    name = "github_api"
    endpoint = "https://api.github.com/search/repositories"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def search(self, query: str, limit: int = 10, freshness: str | None = None) -> list[dict[str, str]]:
        query, limit, _ = _validate_query(query, limit, freshness)
        queries = [query]
        keywords = re.findall(r"[a-z0-9][a-z0-9+.#/-]*", query.lower())
        preferred = [term for term in keywords if term in {"mcp", "git", "git2-rs", "gitoxide", "rust", "python", "javascript", "typescript"}]
        if len(preferred) >= 2:
            queries.append(" ".join(preferred[:3]))
        non_generic = [term for term in keywords if term not in {"alternative", "alternatives", "and", "for", "from", "how", "native", "the", "to", "tool", "tooling", "trend", "trends", "with"}]
        if len(non_generic) >= 2:
            queries.append(" ".join(non_generic[:3]))

        for candidate in dict.fromkeys(queries):
            request = Request(
                self.endpoint + "?" + urlencode({"q": candidate, "per_page": str(min(limit, 10))}),
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "AgentWeb/0.8",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read(2_000_000).decode("utf-8"))
            except Exception as error:
                raise SearchProviderError(f"GitHub repository fallback unavailable: {type(error).__name__}") from error
            items = payload.get("items") if isinstance(payload, dict) else None
            if not isinstance(items, list):
                raise SearchProviderError("GitHub repository fallback returned an invalid result list")
            results: list[dict[str, str]] = []
            for item in items[:limit]:
                if not isinstance(item, dict):
                    continue
                url = item.get("html_url")
                if not isinstance(url, str) or not url.startswith("https://github.com/"):
                    continue
                name = str(item.get("full_name") or item.get("name") or "GitHub repository")
                description = str(item.get("description") or "")
                language = str(item.get("language") or "")
                stars = item.get("stargazers_count")
                details = "; ".join(part for part in (description, f"language: {language}" if language else "", f"stars: {stars}" if isinstance(stars, int) else "") if part)
                result = {"url": url, "title": name, "snippet": details}
                if item.get("updated_at"):
                    result["published_at"] = str(item["updated_at"])
                results.append(result)
            if results:
                return results
        return []


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
            published_at = item.get("published_at", item.get("published_date", item.get("date")))
            if published_at:
                result["published_at"] = str(published_at)
            results.append(result)
        return results


class FallbackSearchProvider:
    def __init__(self, primary: SearchProvider, fallback: SearchProvider | None = None) -> None:
        self.primary = primary
        self.fallback = fallback or DuckDuckGoHTMLProvider()

    def search(self, query: str, limit: int = 10, freshness: str | None = None) -> list[dict[str, str]]:
        try:
            results = self.primary.search(query, limit, freshness)
        except SearchProviderError:
            results = []
        if results:
            return results
        try:
            return self.fallback.search(query, limit, freshness)
        except SearchProviderError:
            return []


def build_search_provider(secret_provider: SecretProvider | None = None) -> SearchProvider:
    config = SearchProviderConfig.from_environment()
    if config.name == "duckduckgo":
            primary = FallbackSearchProvider(DuckDuckGoHTMLProvider(config.timeout), FallbackSearchProvider(BraveSearchHTMLProvider(config.timeout), GitHubRepositorySearchProvider(config.timeout)))
    else:
        secret_provider = secret_provider or build_provider()
        api_key = secret_provider.get(config.api_key_name, required=False)
        primary = FallbackSearchProvider(
            JsonSearchProvider(config.endpoint or "", api_key, config.timeout),
            FallbackSearchProvider(DuckDuckGoHTMLProvider(config.timeout), FallbackSearchProvider(BraveSearchHTMLProvider(config.timeout), GitHubRepositorySearchProvider(config.timeout))),
        )
    from .mode_connectors import build_mode_search_provider
    return build_mode_search_provider(primary)


def search(query: str, limit: int = 10, freshness: str | None = None, provider: SearchProvider | None = None, *, mode: str = "focus", query_count: int | None = None) -> list[dict[str, str]]:
    """Return normalized results; mode-aware providers fan out semantic queries in parallel."""
    if provider is None:
        provider = build_search_provider()
    if query_count is not None and hasattr(provider, "search_many"):
        from .mode_connectors import semantic_queries
        return provider.search_many(semantic_queries(query, query_count), mode=mode, limit=limit, freshness=freshness)  # type: ignore[attr-defined]
    return provider.search(query, limit, freshness)
