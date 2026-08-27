"""Public, no-credential source branches used by AgentWeb's four modes.

The module deliberately uses the Python standard library so the default package
works without API keys or self-hosted services. Optional/self-hosted branches
are documented in ``selfhosting.md`` and are not part of the default runtime.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import unescape
from typing import Callable
from urllib.parse import urlencode, quote, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .fetch import html_to_text


@dataclass(frozen=True)
class ConnectorResult:
    url: str
    title: str
    snippet: str
    published_at: str | None = None
    content_type: str | None = None

    def as_dict(self) -> dict[str, str]:
        result = {"url": self.url, "title": self.title, "snippet": self.snippet}
        if self.published_at:
            result["published_at"] = self.published_at
        if self.content_type:
            result["content_type"] = self.content_type
        return result


def _json_get(url: str, timeout: float = 8.0, headers: dict[str, str] | None = None) -> object:
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "AgentWeb/0.12 (+https://github.com/vincenzo-afk/AgentWeb)", **(headers or {})},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read(3_000_000).decode("utf-8", errors="replace"))


def _xml_get(url: str, timeout: float = 8.0) -> ElementTree.Element:
    request = Request(url, headers={"Accept": "application/atom+xml,application/xml", "User-Agent": "AgentWeb/0.12"})
    with urlopen(request, timeout=timeout) as response:
        return ElementTree.fromstring(response.read(3_000_000))


def semantic_queries(task: str, count: int) -> list[str]:
    """Return semantically distinct, deterministic query variants."""
    task = task.strip()
    count = max(1, min(int(count), 6))
    variants = [
        task,
        f"What are the key facts, evidence, and recent developments about {task}?",
        f"Research {task} using official sources, technical documentation, and independent analysis.",
        f"Compare the strongest publicly documented claims and sources for {task}.",
        f"Find primary data, expert commentary, and counterevidence related to {task}.",
        f"What changed, what is verified, and what remains uncertain about {task}?",
    ]
    return list(dict.fromkeys(variants))[:count]


class _Branch:
    name = "branch"

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        raise NotImplementedError


class DuckDuckGoInstantAnswerBranch(_Branch):
    name = "duckduckgo_instant_answer"

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        payload = _json_get("https://api.duckduckgo.com/?" + urlencode({"q": query, "format": "json", "no_html": 1, "skip_disambig": 0}))
        if not isinstance(payload, dict):
            return []
        results: list[dict[str, str]] = []
        abstract_url = payload.get("AbstractURL")
        abstract = payload.get("AbstractText")
        if isinstance(abstract_url, str) and abstract_url.startswith("http") and isinstance(abstract, str) and abstract.strip():
            results.append({"url": abstract_url, "title": str(payload.get("Heading") or query), "snippet": abstract})
        for item in payload.get("RelatedTopics", []) if isinstance(payload.get("RelatedTopics"), list) else []:
            if not isinstance(item, dict):
                continue
            url, text = item.get("FirstURL"), item.get("Text")
            if isinstance(url, str) and url.startswith("http") and isinstance(text, str):
                results.append({"url": url, "title": text.split(" - ", 1)[0][:160], "snippet": text})
            if len(results) >= limit:
                break
        return results[:limit]


def _public_web_search(query: str, limit: int, freshness: str | None = None) -> list[dict[str, str]]:
    from .search import BingSearchHTMLProvider, BraveSearchHTMLProvider, DuckDuckGoHTMLProvider, SearchProviderError

    errors: list[str] = []
    for provider in (BraveSearchHTMLProvider(), BingSearchHTMLProvider(), DuckDuckGoHTMLProvider()):
        try:
            results = provider.search(query, limit, freshness)
            if results:
                return results
        except SearchProviderError as error:
            errors.append(str(error))
    if errors:
        raise SearchProviderError("; ".join(errors))
    return []


class GeneralWebSearchBranch(_Branch):
    """General public web discovery through ordered HTML search fallbacks."""

    name = "general_web_search"

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        lowered = query.lower()
        if re.search(r"\b(?:capital|population|currency|flag)\s+of\b", lowered) or re.search(r"\b(?:weather|temperature|forecast)\b", lowered):
            return []
        return _public_web_search(query, limit, freshness)


class OfficialDocumentationBranch(_Branch):
    """Search official documentation domains only when the task warrants it."""

    name = "official_documentation"
    _domain_hints = {
        "claude": ["docs.claude.com", "platform.claude.com", "anthropic.com"],
        "anthropic": ["docs.claude.com", "platform.claude.com", "anthropic.com"],
        "openai": ["platform.openai.com", "openai.github.io", "openai.com"],
        "openai agents": ["openai.github.io", "platform.openai.com", "openai.com"],
        "google adk": ["google.github.io", "ai.google.dev", "developers.googleblog.com"],
        "adk": ["google.github.io", "ai.google.dev"],
        "langchain": ["langchain-ai.github.io", "python.langchain.com", "docs.langchain.com"],
        "autogen": ["microsoft.github.io", "github.com/microsoft/autogen", "microsoft.com"],
        "microsoft autogen": ["microsoft.github.io", "github.com/microsoft/autogen", "microsoft.com"],
        "mcp": ["modelcontextprotocol.io", "github.com/modelcontextprotocol"],
        "hugging face": ["huggingface.co"],
        "github": ["docs.github.com", "github.com"],
        "python": ["docs.python.org", "python.org"],
    }

    _seed_urls = {
        "claude": [
            ("https://platform.claude.com/docs/en/api/messages", "Claude Messages API reference"),
            ("https://platform.claude.com/docs/en/api/overview", "Claude API overview"),
        ],
        "anthropic": [
            ("https://platform.claude.com/docs/en/api/messages", "Claude Messages API reference"),
            ("https://platform.claude.com/docs/en/api/overview", "Claude API overview"),
        ],
        "openai": [
            ("https://platform.openai.com/docs/api-reference/responses", "OpenAI Responses API reference"),
            ("https://platform.openai.com/docs/overview", "OpenAI developer documentation"),
        ],
        "openai agents": [
            ("https://openai.github.io/openai-agents-python/", "OpenAI Agents SDK documentation"),
            ("https://platform.openai.com/docs/guides/agents", "OpenAI Agents guide"),
        ],
        "google adk": [
            ("https://google.github.io/adk-docs/", "Google Agent Development Kit documentation"),
            ("https://google.github.io/adk-docs/get-started/quickstart/", "Google ADK quickstart"),
        ],
        "adk": [
            ("https://google.github.io/adk-docs/", "Google Agent Development Kit documentation"),
        ],
        "langchain": [
            ("https://docs.langchain.com/oss/python/langchain/retrieval", "LangChain retrieval documentation"),
            ("https://www.langchain.com/retrieval", "LangChain retrieval overview"),
        ],
        "autogen": [
            ("https://microsoft.github.io/autogen/stable/", "Microsoft AutoGen documentation"),
            ("https://github.com/microsoft/autogen", "Microsoft AutoGen repository"),
        ],
        "microsoft autogen": [
            ("https://microsoft.github.io/autogen/stable/", "Microsoft AutoGen documentation"),
        ],
        "mcp": [("https://modelcontextprotocol.io/docs/getting-started/intro", "Model Context Protocol documentation")],
        "hugging face": [("https://huggingface.co/docs", "Hugging Face documentation")],
        "github": [("https://docs.github.com/en", "GitHub documentation")],
        "python": [("https://docs.python.org/3/", "Python documentation")],
    }

    @staticmethod
    def _host_matches(url: str, allowed: tuple[str, ...]) -> bool:
        hostname = (urlparse(url).hostname or "").lower().rstrip(".")
        return any(hostname == domain or hostname.endswith("." + domain) for domain in allowed)

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        lowered = query.lower()
        if not re.search(r"\b(?:official|documentation|docs|reference|api|sdk|how to|guide)\b", lowered):
            return []
        domains: list[str] = []
        seeds: list[dict[str, str]] = []
        matched_hints = [(hint, candidates) for hint, candidates in self._domain_hints.items() if hint in lowered]
        matched_hints.sort(key=lambda item: len(item[0]), reverse=True)
        hint_groups = {
            "openai agents": "openai",
            "openai": "openai",
            "google adk": "google adk",
            "adk": "google adk",
            "microsoft autogen": "autogen",
            "autogen": "autogen",
            "anthropic": "claude",
            "claude": "claude",
        }
        processed_groups: set[str] = set()
        for hint, candidates in matched_hints:
            group = hint_groups.get(hint, hint)
            if group in processed_groups:
                continue
            processed_groups.add(group)
            domains.extend(candidates)
            seed_key = hint if hint in self._seed_urls else group
            for url, title in self._seed_urls.get(seed_key, []):
                seeds.append({"url": url, "title": title, "snippet": "First-party documentation seed for this product."})
        if not domains:
            return []
        scoped_query = query + " " + " ".join(f"site:{domain}" for domain in list(dict.fromkeys(domains))[:3])
        try:
            results = _public_web_search(scoped_query, limit, freshness)
        except Exception:
            try:
                results = _public_web_search(query, min(20, max(limit * 2, limit)), freshness)
            except Exception:
                results = []
        allowed = tuple(domain.lower() for domain in domains)
        filtered = [item for item in results if self._host_matches(item.get("url", ""), allowed)]
        merged: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in seeds + filtered:
            url = item.get("url", "")
            if url and url not in seen:
                seen.add(url)
                merged.append(item)
            if len(merged) >= limit:
                break
        return merged


class RedditJSONBranch(_Branch):
    name = "reddit_json"

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        payload = _json_get("https://www.reddit.com/search.json?" + urlencode({"q": query, "sort": "relevance", "limit": min(limit, 25), "raw_json": 1}))
        results: list[dict[str, str]] = []
        children = payload.get("data", {}).get("children", []) if isinstance(payload, dict) else []
        for child in children:
            data = child.get("data", {}) if isinstance(child, dict) else {}
            permalink = data.get("permalink")
            if not isinstance(permalink, str):
                continue
            url = "https://www.reddit.com" + permalink
            results.append({"url": url, "title": str(data.get("title") or "Reddit discussion"), "snippet": str(data.get("selftext") or data.get("title") or "")[:500], "published_at": str(data.get("created_utc") or "")})
        return results[:limit]


class WikidataBranch(_Branch):
    name = "wikidata"

    @staticmethod
    def _entity_query(query: str) -> str:
        match = re.search(r"\b(?:capital|population|currency|flag)\s+(?:of\s+)?([A-Za-z][A-Za-z .'-]{1,60})", query, re.I)
        return match.group(1).strip(" .?!") if match else query

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        payload = _json_get("https://www.wikidata.org/w/api.php?" + urlencode({"action": "wbsearchentities", "search": self._entity_query(query), "language": "en", "format": "json", "limit": min(limit, 10)}))
        results: list[dict[str, str]] = []
        for item in payload.get("search", []) if isinstance(payload, dict) else []:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            entity_id = str(item["id"])
            results.append({"url": f"https://www.wikidata.org/wiki/{entity_id}", "title": str(item.get("label") or entity_id), "snippet": str(item.get("description") or "Wikidata entity")})
        return results[:limit]


class QuickFactBranch(_Branch):
    name = "quick_fact_apis"

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        lowered = query.lower()
        if re.search(r"\b(weather|temperature|forecast)\b", lowered):
            city_match = re.search(r"\b(?:in|at|for)\s+([A-Za-z][A-Za-z .'-]{1,60})", query, re.I)
            if city_match:
                city = city_match.group(1).strip(" .?!")
                geo = _json_get("https://geocoding-api.open-meteo.com/v1/search?" + urlencode({"name": city, "count": 1, "language": "en", "format": "json"}))
                item = geo.get("results", [None])[0] if isinstance(geo, dict) and geo.get("results") else None
                if isinstance(item, dict):
                    weather = _json_get("https://api.open-meteo.com/v1/forecast?" + urlencode({"latitude": item.get("latitude"), "longitude": item.get("longitude"), "current": "temperature_2m,wind_speed_10m"}))
                    current = weather.get("current", {}) if isinstance(weather, dict) else {}
                    return [{"url": "https://open-meteo.com/", "title": f"Current weather in {city}", "snippet": json.dumps(current, sort_keys=True), "content_type": "application/json"}]
        country_match = re.search(r"\b(?:capital|population|currency|flag)\s+(?:of\s+)?([A-Za-z][A-Za-z .'-]{1,60})", query, re.I)
        if country_match:
            country = country_match.group(1).strip(" .?!")
            try:
                entity_search = WikidataBranch().search(country, limit=1)
                if entity_search:
                    entity_url = entity_search[0]["url"]
                    entity_id = entity_url.rsplit("/", 1)[-1]
                    entity = _json_get("https://www.wikidata.org/wiki/Special:EntityData/" + quote(entity_id) + ".json")
                    entity_data = entity.get("entities", {}).get(entity_id, {}) if isinstance(entity, dict) else {}
                    claims = entity_data.get("claims", {}) if isinstance(entity_data, dict) else {}
                    property_id = {"capital": "P36", "population": "P1082", "currency": "P38", "flag": "P41"}.get(country_match.group(0).split()[0].lower(), "P36")
                    claim = claims.get(property_id, [{}])[0] if isinstance(claims.get(property_id), list) else {}
                    datavalue = claim.get("mainsnak", {}).get("datavalue", {}) if isinstance(claim, dict) else {}
                    value = datavalue.get("value", {}) if isinstance(datavalue, dict) else {}
                    if isinstance(value, dict) and value.get("id"):
                        target_id = str(value["id"])
                        target = _json_get("https://www.wikidata.org/w/api.php?" + urlencode({"action": "wbgetentities", "ids": target_id, "props": "labels|descriptions", "languages": "en", "format": "json"}))
                        label = target.get("entities", {}).get(target_id, {}).get("labels", {}).get("en", {}).get("value") if isinstance(target, dict) else None
                        if label:
                            return [{"url": entity_url, "title": country, "snippet": f"{country}'s {country_match.group(0).split()[0].lower()} is {label}.", "content_type": "application/json"}]
            except Exception:
                pass
            try:
                payload = _json_get("https://restcountries.com/v3.1/name/" + quote(country) + "?fields=name,capital,population,currencies,flags")
                item = payload[0] if isinstance(payload, list) and payload else None
                if isinstance(item, dict):
                    return [{"url": "https://restcountries.com/", "title": str(item.get("name", {}).get("common") or country), "snippet": json.dumps(item, sort_keys=True), "content_type": "application/json"}]
            except Exception:
                pass
        if "hacker news" in lowered or "top stories" in lowered:
            ids = _json_get("https://hacker-news.firebaseio.com/v0/topstories.json")
            results: list[dict[str, str]] = []
            for story_id in ids[:limit] if isinstance(ids, list) else []:
                item = _json_get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
                if isinstance(item, dict) and isinstance(item.get("url"), str):
                    results.append({"url": item["url"], "title": str(item.get("title") or "Hacker News story"), "snippet": f"Hacker News score: {item.get('score', 0)}"})
            return results
        if re.search(r"\b(?:book|books|isbn|author)\b", lowered):
            payload = _json_get("https://openlibrary.org/search.json?" + urlencode({"q": query, "limit": limit, "fields": "key,title,author_name,first_publish_year"}))
            results = []
            for item in payload.get("docs", []) if isinstance(payload, dict) else []:
                if isinstance(item, dict) and item.get("key"):
                    results.append({"url": "https://openlibrary.org" + str(item["key"]), "title": str(item.get("title") or "Book"), "snippet": ", ".join(str(x) for x in (item.get("author_name") or [])[:3]) + (f"; first published {item.get('first_publish_year')}" if item.get("first_publish_year") else "")})
            return results[:limit]
        return []


class WikipediaBranch(_Branch):
    name = "wikipedia_api"

    @staticmethod
    def _search_query(query: str) -> str:
        match = re.search(r"\b(?:capital|population|currency|flag)\s+(?:of\s+)?([A-Za-z][A-Za-z .'-]{1,60})", query, re.I)
        return f"{match.group(1).strip(' .?!')} capital" if match else query

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        payload = _json_get("https://en.wikipedia.org/w/api.php?" + urlencode({"action": "query", "list": "search", "srsearch": self._search_query(query), "format": "json", "srlimit": min(limit, 10), "utf8": 1}))
        results = []
        for item in payload.get("query", {}).get("search", []) if isinstance(payload, dict) else []:
            if not isinstance(item, dict) or not item.get("pageid"):
                continue
            title = str(item.get("title") or "Wikipedia")
            results.append({"url": "https://en.wikipedia.org/?curid=" + str(item["pageid"]), "title": title, "snippet": html_to_text(unescape(str(item.get("snippet") or "")))})
        return results[:limit]


class DBpediaBranch(_Branch):
    name = "dbpedia_sparql"

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        payload = _json_get("https://lookup.dbpedia.org/api/search?" + urlencode({"query": query, "format": "JSON", "maxResults": min(limit, 10)}), headers={"Accept": "application/json"})
        results = []
        for item in payload.get("docs", []) if isinstance(payload, dict) else []:
            if isinstance(item, dict) and isinstance(item.get("resource"), str):
                results.append({"url": item["resource"], "title": str(item.get("label") or "DBpedia entity"), "snippet": str(item.get("comment") or "")[:500]})
        return results[:limit]


class OpenReviewBranch(_Branch):
    name = "openreview_net"

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        payload = _json_get("https://api2.openreview.net/notes?" + urlencode({"content.title": query, "limit": min(limit, 10)}))
        results = []
        for item in payload.get("notes", []) if isinstance(payload, dict) else []:
            if isinstance(item, dict) and item.get("id"):
                content = item.get("content") or {}
                title = content.get("title", {}) if isinstance(content, dict) else {}
                title_value = title.get("value") if isinstance(title, dict) else title
                results.append({"url": f"https://openreview.net/forum?id={item['id']}", "title": str(title_value or "OpenReview paper"), "snippet": "OpenReview scholarly record"})
        return results[:limit]


class WaybackCDXBranch(_Branch):
    name = "wayback_cdx"

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        if not query.startswith(("http://", "https://")):
            return []
        payload = _json_get("https://web.archive.org/cdx/search/cdx?" + urlencode({"url": query, "output": "json", "filter": "statuscode:200", "fl": "timestamp,original,statuscode", "collapse": "digest", "limit": min(limit, 20)}))
        results = []
        for row in payload[1:] if isinstance(payload, list) and payload else []:
            if isinstance(row, list) and len(row) >= 2:
                timestamp, original = str(row[0]), str(row[1])
                results.append({"url": f"https://web.archive.org/web/{timestamp}/{original}", "title": f"Wayback snapshot {timestamp}", "snippet": f"Archived snapshot of {original}", "published_at": timestamp})
        return results[:limit]


class StackExchangeBranch(_Branch):
    name = "stack_exchange_network"

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        payload = _json_get("https://api.stackexchange.com/2.3/search/advanced?" + urlencode({"q": query, "site": "stackoverflow", "pagesize": min(limit, 20), "order": "desc", "sort": "relevance", "filter": "default"}))
        results = []
        for item in payload.get("items", []) if isinstance(payload, dict) else []:
            if isinstance(item, dict) and isinstance(item.get("link"), str):
                results.append({"url": item["link"], "title": str(item.get("title") or "Stack Exchange question"), "snippet": "; ".join(str(tag) for tag in item.get("tags", [])[:8])})
        return results[:limit]


class AcademicBranch(_Branch):
    name = "academic_apis"

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        try:
            payload = _json_get("https://api.openalex.org/works?" + urlencode({"search": query, "per-page": min(limit, 10), "select": "id,title,publication_year,primary_location"}))
            for item in payload.get("results", []) if isinstance(payload, dict) else []:
                location = item.get("primary_location") or {}
                source = location.get("source") or {}
                url = location.get("landing_page_url") or item.get("id")
                if isinstance(url, str) and url.startswith("http"):
                    results.append({"url": url, "title": str(item.get("title") or "Academic work"), "snippet": f"OpenAlex; year: {item.get('publication_year')}; venue: {source.get('display_name', '')}"})
        except Exception:
            pass
        try:
            payload = _json_get("https://api.semanticscholar.org/graph/v1/paper/search?" + urlencode({"query": query, "limit": min(limit, 10), "fields": "title,url,abstract,year"}))
            for item in payload.get("data", []) if isinstance(payload, dict) else []:
                url = item.get("url")
                if isinstance(url, str) and url.startswith("http"):
                    results.append({"url": url, "title": str(item.get("title") or "Semantic Scholar paper"), "snippet": f"{str(item.get('abstract') or '')[:300]} year: {item.get('year')}"})
        except Exception:
            pass
        return results[:limit]


class ArxivBranch(_Branch):
    name = "arxiv"

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        root = _xml_get("http://export.arxiv.org/api/query?" + urlencode({"search_query": f"all:{query}", "start": 0, "max_results": min(limit, 10)}))
        results = []
        atom = "{http://www.w3.org/2005/Atom}"
        for entry in root.findall(atom + "entry"):
            link = entry.find(atom + "id")
            title = entry.find(atom + "title")
            summary = entry.find(atom + "summary")
            if link is not None and link.text:
                results.append({"url": link.text.strip(), "title": (title.text or "arXiv paper").strip() if title is not None else "arXiv paper", "snippet": (summary.text or "").strip()[:500] if summary is not None else ""})
        return results[:limit]


class PubMedBranch(_Branch):
    name = "pubmed_eutilities"

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        ids = _json_get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urlencode({"db": "pubmed", "term": query, "retmode": "json", "retmax": min(limit, 10)}))
        id_list = ids.get("esearchresult", {}).get("idlist", []) if isinstance(ids, dict) else []
        if not id_list:
            return []
        summary = _json_get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + urlencode({"db": "pubmed", "id": ",".join(id_list), "retmode": "json"}))
        results = []
        for pub_id in id_list:
            item = summary.get("result", {}).get(pub_id, {}) if isinstance(summary, dict) else {}
            results.append({"url": f"https://pubmed.ncbi.nlm.nih.gov/{pub_id}/", "title": str(item.get("title") or "PubMed article"), "snippet": str(item.get("sortpubdate") or "PubMed record")})
        return results[:limit]


class ProjectGutenbergBranch(_Branch):
    name = "project_gutenberg"

    def search(self, query: str, limit: int = 5, freshness: str | None = None) -> list[dict[str, str]]:
        payload = _json_get("https://gutendex.com/books?" + urlencode({"search": query, "page": 1}))
        results = []
        for item in payload.get("results", []) if isinstance(payload, dict) else []:
            if isinstance(item, dict) and item.get("id"):
                authors = ", ".join(str(author.get("name")) for author in item.get("authors", [])[:2] if isinstance(author, dict))
                results.append({"url": f"https://www.gutenberg.org/ebooks/{item['id']}", "title": str(item.get("title") or "Project Gutenberg book"), "snippet": authors})
        return results[:limit]


class BranchSearchProvider:
    """Run mode-specific branches concurrently and merge duplicate URLs."""
    supports_mode_search = True

    def __init__(self, primary, branches: dict[str, list[_Branch]] | None = None, timeout: float = 8.0) -> None:
        self.primary = primary
        self.branches = branches or {}
        self.timeout = timeout
        self.last_metadata: dict[str, object] = {}

    def search(self, query: str, limit: int = 10, freshness: str | None = None) -> list[dict[str, str]]:
        return self.search_many([query], mode="focus", limit=limit, freshness=freshness)

    def search_many(self, queries: list[str], mode: str, limit: int = 10, freshness: str | None = None) -> list[dict[str, str]]:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        selected = list(self.branches.get(mode, self.branches.get("focus", [])))
        jobs: list[tuple[str, Callable[[], list[dict[str, str]]]]] = []
        for query in queries:
            jobs.append(("primary", lambda query=query: self.primary.search(query, limit, freshness)))
            for branch in selected:
                jobs.append((branch.name, lambda branch=branch, query=query: branch.search(query, limit, freshness)))
        merged: dict[str, dict[str, str]] = {}
        branch_counts: dict[str, int] = {}
        failures: dict[str, str] = {}
        priority = {"quick_fact_apis": 0, "official_documentation": 1, "primary": 2, "wikipedia_api": 3, "wikidata": 4, "dbpedia_sparql": 5, "academic_apis": 6, "arxiv": 7, "pubmed_eutilities": 8, "openreview_net": 9, "stack_exchange_network": 10, "project_gutenberg": 11, "wayback_cdx": 12, "general_web_search": 13, "github_api": 14, "reddit_json": 15, "duckduckgo_instant_answer": 16}
        with ThreadPoolExecutor(max_workers=min(16, max(1, len(jobs)))) as pool:
            futures = {pool.submit(job): name for name, job in jobs}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    items = future.result() or []
                    branch_counts[name] = branch_counts.get(name, 0) + len(items)
                    for item in items:
                        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
                            continue
                        url = item["url"]
                        candidate = {"url": url, "title": str(item.get("title", "")), "snippet": str(item.get("snippet", "")), "_branch": name}
                        for key in ("published_at", "content_type"):
                            if item.get(key):
                                candidate[key] = str(item[key])
                        if url not in merged:
                            merged[url] = candidate
                        else:
                            current = merged[url]
                            if priority.get(name, 50) < priority.get(str(current.get("_branch", "")), 50):
                                current["_branch"] = name
                                current["title"] = candidate["title"] or current.get("title", "")
                                current["snippet"] = candidate["snippet"] or current.get("snippet", "")
                                for key in ("published_at", "content_type"):
                                    if candidate.get(key):
                                        current[key] = candidate[key]
                            elif len(candidate.get("snippet", "")) > len(current.get("snippet", "")):
                                current["snippet"] = candidate["snippet"]
                            for key in ("published_at", "content_type"):
                                if candidate.get(key) and not current.get(key):
                                    current[key] = candidate[key]
                except Exception as error:
                    failures[name] = type(error).__name__
        ordered = sorted(merged.values(), key=lambda item: (priority.get(str(item.get("_branch", "")), 50), -len(str(item.get("snippet", ""))), str(item.get("url", ""))))
        for item in ordered:
            item.pop("_branch", None)
        self.last_metadata = {"queries": queries, "branches": sorted({name for name, _ in jobs}), "branch_counts": branch_counts, "failures": failures, "deduped_count": len(merged), "selected_branch_order": [str(item.get("url")) for item in ordered[: max(1, min(int(limit) * max(1, len(queries)), 100))]]}
        return ordered[: max(1, min(int(limit) * max(1, len(queries)), 100))]


def build_mode_search_provider(primary) -> BranchSearchProvider:
    """Build the default public branch graph around the existing primary provider."""
    from .search import GitHubRepositorySearchProvider
    github = GitHubRepositorySearchProvider()
    general_web = GeneralWebSearchBranch()
    official_docs = OfficialDocumentationBranch()
    flash = [general_web, official_docs, github, DuckDuckGoInstantAnswerBranch(), WikidataBranch(), QuickFactBranch(), RedditJSONBranch()]
    focus = [general_web, official_docs, github, DuckDuckGoInstantAnswerBranch(), WikidataBranch(), QuickFactBranch(), WikipediaBranch(), RedditJSONBranch()]
    dive = focus + [StackExchangeBranch(), AcademicBranch(), ArxivBranch(), PubMedBranch(), OpenReviewBranch(), DBpediaBranch(), ProjectGutenbergBranch()]
    monitor = [general_web, official_docs, github, RedditJSONBranch(), WaybackCDXBranch(), DuckDuckGoInstantAnswerBranch(), WikidataBranch(), QuickFactBranch(), WikipediaBranch()]
    return BranchSearchProvider(primary, {"flash": flash, "focus": focus, "dive": dive, "monitor": monitor})
