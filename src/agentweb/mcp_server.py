"""Model-agnostic MCP server exposing AgentWeb's bounded public capabilities."""
from __future__ import annotations

import argparse
import json
from typing import Literal

from mcp.server import MCPServer

from .engine import AgentWebEngine
from .memory import MemoryStore
from .planner import Planner

ResearchMode = Literal["flash", "focus", "dive", "monitor"]
MonitorFrequency = Literal["minutely", "hourly", "daily"]


def _bounded_text(value: str, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} must contain between 1 and {maximum} characters")
    return normalized


def _compact_source(source: object, *, keep_media: bool = True, include_detail: bool = False) -> dict:
    if not isinstance(source, dict):
        return {}
    compact = {key: source.get(key) for key in ("id", "url", "title", "trust_score", "cited", "published_at", "content_type", "extraction_confidence") if source.get(key) is not None}
    compact["snippet"] = str(source.get("snippet", ""))[:900]
    structured = source.get("structured_data")
    if isinstance(structured, dict):
        reduced: dict[str, object] = {}
        segments = structured.get("evidence_segments")
        if include_detail and isinstance(segments, dict):
            reduced["evidence_segments"] = {str(key): str(value)[:300] for key, value in list(segments.items())[:8]}
        connector_fields = structured.get("connector_fields")
        if include_detail and isinstance(connector_fields, dict):
            reduced["connector_fields"] = {str(key): str(value)[:200] for key, value in list(connector_fields.items())[:12]}
        media = structured.get("media")
        if keep_media and isinstance(media, dict):
            media_fields = ("title", "author_name", "author_url", "provider_name", "provider_url", "publishDate", "uploadDate", "lengthSeconds", "viewCount", "transcript_language")
            reduced["media"] = {key: media.get(key) for key in media_fields if media.get(key) not in (None, "")}
            if isinstance(media.get("transcript"), str):
                reduced["media"]["transcript"] = media["transcript"][:1_500]
        if reduced:
            compact["structured_data"] = reduced
    return compact


def _compact_structured_output(value: object, *, facet_chars: int = 180) -> object:
    if not isinstance(value, dict):
        return value
    if "frameworks" in value:
        output = {key: value.get(key) for key in ("task", "ranking", "references", "evidence_gaps", "unverified_policy") if key in value}
        frameworks = []
        for framework in value.get("frameworks", [])[:5]:
            if not isinstance(framework, dict):
                continue
            facets = {}
            for key, facet in list((framework.get("facets") or {}).items())[:12]:
                if isinstance(facet, dict):
                    facets[key] = {"status": facet.get("status"), "evidence": str(facet.get("evidence", ""))[:facet_chars], "source_ids": list(facet.get("source_ids") or [])[:3]}
            frameworks.append({"framework": framework.get("framework"), "facets": facets, "source_ids": list(framework.get("source_ids") or [])[:12]})
        output["frameworks"] = frameworks
        output["references"] = [{"id": item.get("id"), "url": item.get("url"), "title": item.get("title")} for item in (value.get("references") or [])[:20] if isinstance(item, dict)]
        return output
    return value


def _compact_research_response(payload: dict, *, include_all_evidence: bool = False, max_answer_chars: int = 18_000, max_sources: int | None = None, include_detail: bool | None = None, max_total_chars: int = 32_000) -> dict:
    """Keep MCP responses answer-first and bounded even when full evidence is requested."""
    if not isinstance(payload, dict):
        return {"status": "failed", "error": "invalid research response"}
    compact = dict(payload)
    if isinstance(compact.get("answer"), str):
        compact["answer"] = compact["answer"][:max_answer_chars]
    sources = compact.get("sources")
    if isinstance(sources, list):
        source_limit = max_sources if max_sources is not None else (14 if include_all_evidence else 8)
        detail = include_all_evidence if include_detail is None else include_detail
        compact["sources"] = [_compact_source(source, include_detail=detail) for source in sources[:source_limit]]
    citations = compact.get("citations")
    if isinstance(citations, list):
        compact["citations"] = citations[:80]
    if "structured_output" in compact:
        compact["structured_output"] = _compact_structured_output(compact.get("structured_output"), facet_chars=180)
    compact.pop("actions", None)
    compact.pop("plan", None)
    compact.pop("selection_logic", None)
    if len(json.dumps(compact, ensure_ascii=False)) > max_total_chars:
        compact["sources"] = compact.get("sources", [])[:6] if isinstance(compact.get("sources"), list) else compact.get("sources")
        compact["citations"] = compact.get("citations", [])[:60] if isinstance(compact.get("citations"), list) else compact.get("citations")
        trace_value = compact.get("research_trace")
        if isinstance(trace_value, dict):
            compact["research_trace"] = {key: trace_value.get(key) for key in ("queries", "final_evidence", "candidate_count", "ranked_count", "selected_count", "stop_reason") if key in trace_value}
    if len(json.dumps(compact, ensure_ascii=False)) > max_total_chars and isinstance(compact.get("answer"), str):
        compact["answer"] = compact["answer"][:max(8_000, max_total_chars // 2)]
    trace = compact.get("research_trace")
    if isinstance(trace, dict):
        compact["research_trace"] = {
            "queries": list(trace.get("queries") or [])[:20],
            "waves": [
                {key: wave.get(key) for key in ("round", "queries", "query_count", "candidate_count", "fetched_count", "evidence", "provider_metadata") if key in wave}
                for wave in (trace.get("waves") or [])[:6] if isinstance(wave, dict)
            ],
            "final_evidence": trace.get("final_evidence"),
            "candidate_count": trace.get("candidate_count"),
            "ranked_count": trace.get("ranked_count"),
            "selected_count": trace.get("selected_count"),
            "stop_reason": trace.get("stop_reason"),
        }
    return compact


class AgentWebMCPTools:
    """MCP tool facade with bounded inputs and no credential/session exposure."""

    def __init__(self, engine: AgentWebEngine) -> None:
        self.engine = engine

    def capabilities(self) -> dict:
        return {
            "modes": {
                "flash": {"semantic_queries": 2, "fetch_pages": 4, "selected_sources": 2, "description": "fast answer with light retrieval"},
                "focus": {"semantic_queries": 4, "fetch_pages": 10, "selected_sources": 6, "description": "multi-source grounded answer"},
                "dive": {"semantic_queries": 6, "fetch_pages": 18, "selected_sources": 10, "description": "deep research across public source types"},
                "monitor": {"semantic_queries": "adaptive", "description": "scheduled diff checks and public-source monitoring"},
            },
            "always_on_branches": ["github_api", "reddit_json"],
            "public_branches": ["general_web_search", "official_documentation", "github_api", "reddit_json", "duckduckgo_instant_answer", "wikidata", "wikipedia_api", "quick_fact_apis", "stack_exchange_network", "academic_apis", "arxiv", "pubmed_eutilities", "openreview_net", "dbpedia_sparql", "wayback_cdx", "open_library", "project_gutenberg"],
            "parallel_research": {"max_tasks": 12, "max_concurrency": 8, "description": "run independent adaptive research tasks concurrently"},
            "adaptive_research": {"max_rounds": 6, "max_concurrency": 8, "evidence_target": 12, "stop_reasons": ["evidence_gate_satisfied", "wall_clock_budget_reached", "query_budget_reached", "max_rounds_reached", "candidate_budget_reached"]},
            "model_routing": getattr(self.engine, "model_router", None).status() if getattr(self.engine, "model_router", None) else {"enabled": False, "reason": "not_available"},
            "web_support": {"general_search": "credential-free public web discovery", "official_documentation": "selective first-party retrieval for configured documentation domains", "direct_urls": "public HTTP(S) page extraction"},
            "official_documentation_domains": ["platform.claude.com", "docs.claude.com", "developers.openai.com", "platform.openai.com", "openai.github.io", "adk.dev", "google.github.io", "ai.google.dev", "docs.langchain.com", "langchain-ai.github.io", "microsoft.github.io", "modelcontextprotocol.io", "docs.github.com", "docs.python.org"],
            "intent_policies": {"factual": "explicit claim-value gate; abstain when evidence does not state the answer", "official": "target-domain seeds plus authoritative-host reranking", "comparison": "entity/facet normalization with framework-diverse fetches and claim citations", "exploratory": "broad public discovery with lower authority requirements", "technical": "official docs, specifications, papers, and repositories preferred", "current": "freshness and release/changelog signals preferred"},
            "response_policy": {"default_include_all_evidence": False, "answer_first": True, "max_answer_chars": 18_000, "parallel_max_answer_chars_per_task": 9_000, "raw_page_structures": "omitted", "note": "Request include_all_evidence only when raw source detail is needed; responses remain bounded."},
            "media_support": {"youtube": "metadata and public captions when exposed", "generic_video": "OpenGraph media metadata", "credentials": "not accepted"},
            "excluded_self_hosted_or_keyed": ["see selfhosting.md"],
        }

    def research(self, task: str, mode: ResearchMode = "focus", max_rounds: int | None = None, max_concurrency: int | None = None, evidence_target: int | None = None, include_all_evidence: bool = False) -> dict:
        normalized_task = _bounded_text(task, field="task", maximum=2_000)
        try:
            try:
                response = self.engine.solve(normalized_task, mode=mode, output_format="text", max_rounds=max_rounds, max_concurrency=max_concurrency, evidence_target=evidence_target, include_all_evidence=include_all_evidence)
            except TypeError as error:
                if "unexpected keyword argument" not in str(error):
                    raise
                response = self.engine.solve(normalized_task, mode=mode, output_format="text")
            return _compact_research_response(response.to_dict(), include_all_evidence=include_all_evidence, max_answer_chars=18_000, max_sources=10 if include_all_evidence else 6, max_total_chars=32_000)
        except Exception as error:
            return {"status": "failed", "error": str(error) or type(error).__name__, "error_type": type(error).__name__, "mode": mode}

    def parallel_research(self, tasks: list[str], mode: ResearchMode = "focus", max_concurrency: int = 4, max_rounds: int | None = None, evidence_target: int | None = None, include_all_evidence: bool = False) -> dict:
        if not isinstance(tasks, list) or not tasks or len(tasks) > 12:
            raise ValueError("tasks must contain between 1 and 12 items")
        normalized_tasks = [_bounded_text(task, field="task", maximum=2_000) for task in tasks]
        if isinstance(max_concurrency, bool) or not isinstance(max_concurrency, int) or not 1 <= max_concurrency <= 8:
            raise ValueError("max_concurrency must be an integer between 1 and 8")
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(max_concurrency, len(normalized_tasks))) as pool:
            raw_results = list(pool.map(lambda task: self.research(task, mode, max_rounds, max_concurrency, evidence_target, include_all_evidence), normalized_tasks))
        results = [_compact_research_response(result, include_all_evidence=include_all_evidence, max_answer_chars=6_000, max_sources=4 if include_all_evidence else 3, include_detail=False, max_total_chars=12_000) for result in raw_results]
        return {"status": "complete", "mode": mode, "task_count": len(results), "results": results, "payload_policy": {"answer_first": True, "include_all_evidence": include_all_evidence, "max_answer_chars_per_task": 6_000, "sources_per_task": 4 if include_all_evidence else 3, "raw_page_structures": "omitted"}}

    def extract_page(self, url: str, requested_schema: dict | None = None) -> dict:
        normalized_url = _bounded_text(url, field="url", maximum=2_048)
        try:
            if requested_schema is None:
                return self.engine.extract(normalized_url)
            return self.engine.extract(normalized_url, requested_schema=requested_schema)
        except Exception as error:
            return {"status": "failed", "url": normalized_url, "error": str(error) or type(error).__name__, "error_type": type(error).__name__, "retryable": type(error).__name__ in {"TimeoutError", "URLError"}}


    def crawl(self, url: str, max_pages: int = 10, depth: int = 1, url_pattern: str | None = None) -> dict:
        result = self.engine.crawler.crawl(_bounded_text(url, field="url", maximum=2_048), max_pages=max_pages, depth=depth, url_pattern=url_pattern)
        return {"crawl_id": result.crawl_id, "pages_crawled": result.pages_crawled, "truncated": result.truncated, "pages": [page.__dict__ for page in result.pages]}

    def browser_open(self, url: str, actions: list[dict] | None = None) -> dict:
        normalized_url = _bounded_text(url, field="url", maximum=2_048)
        try:
            session = self.engine.browser_open(normalized_url, actions=actions or [])
            return {"status": getattr(session, "status", "complete"), "url": normalized_url, "title": getattr(session, "title", ""), "text": getattr(session, "text", ""), "actions": getattr(session, "actions", []), "warnings": getattr(session, "warnings", []), "error": getattr(session, "error", None)}
        except Exception as error:
            return {"status": "failed", "url": normalized_url, "error": str(error) or type(error).__name__, "error_type": type(error).__name__, "retryable": type(error).__name__ in {"BrowserUnavailableError", "BrowserTimeoutError"}}

    def create_monitor(self, task: str, frequency: MonitorFrequency = "daily", webhook_url: str | None = None, change_policy: dict | None = None) -> dict:
        normalized_task = _bounded_text(task, field="task", maximum=2_000)
        if webhook_url is None and change_policy is None:
            monitor = self.engine.create_monitor(normalized_task, frequency=frequency)
        else:
            monitor = self.engine.create_monitor(normalized_task, frequency=frequency, webhook_url=webhook_url, change_policy=change_policy)
        return monitor.to_dict() if hasattr(monitor, "to_dict") else {"id": monitor.id, "task": monitor.task, "frequency": monitor.frequency, "target_url": monitor.target_url, "status": monitor.status}

    def check_monitor(self, monitor_id: str) -> dict:
        normalized_id = _bounded_text(monitor_id, field="monitor_id", maximum=120)
        try:
            monitor = self.engine.memory.get_monitor(normalized_id)
            if monitor is None:
                return {"status": "failed", "error": "monitor not found", "error_type": "MonitorNotFound", "monitor_id": normalized_id}
            return self.engine.check_monitor(monitor).to_dict()
        except Exception as error:
            return {"status": "failed", "error": str(error) or type(error).__name__, "error_type": type(error).__name__, "monitor_id": normalized_id}

    def list_monitors(self) -> list[dict]:
        return self.engine.memory.list_monitors()

    def create_plan(self, task: str, mode: ResearchMode | None = None, skill: str | None = None, inputs: dict | None = None) -> dict:
        return self.engine.create_plan(_bounded_text(task, field="task", maximum=2_000), mode=mode, skill=skill, inputs=inputs or {})

    def execute_plan(self, plan_id: str, output_format: str | None = None) -> dict:
        normalized_id = _bounded_text(plan_id, field="plan_id", maximum=120)
        try:
            return self.engine.execute_plan(normalized_id, output_format=output_format)
        except Exception as error:
            return {"status": "failed", "error": str(error) or type(error).__name__, "error_type": type(error).__name__, "plan_id": normalized_id}



def create_mcp_server(engine: AgentWebEngine | None = None) -> MCPServer:
    tools = AgentWebMCPTools(engine or AgentWebEngine())
    mcp = MCPServer(
        "AgentWeb",
        instructions=(
            "Use AgentWeb for bounded, citation-oriented public web research. "
            "Flash, Focus, Dive, and Monitor determine retrieval depth and polling behavior. "
            "AgentWeb runs independent source branches concurrently, evaluates evidence after each wave, and continues with targeted follow-up searches until its evidence gate or a transparent resource limit is reached. "
            "Responses are answer-first and compact by default; raw page structures are omitted. Use agentweb_parallel_research for separable subquestions and rely on its bounded per-task answers. Set include_all_evidence only when additional source detail is necessary. Do not infer facts beyond returned evidence; self-hosted and credentialed integrations are documented in selfhosting.md."
        ),
    )

    @mcp.tool()
    def agentweb_capabilities() -> dict:
        """List supported modes, public source branches, and excluded integrations."""
        return tools.capabilities()

    @mcp.tool()
    def agentweb_research(task: str, mode: ResearchMode = "focus", max_rounds: int | None = None, max_concurrency: int | None = None, evidence_target: int | None = None, include_all_evidence: bool = False) -> dict:
        """Run bounded adaptive research; returns a compact answer, citations, and bounded source evidence."""
        return tools.research(task, mode, max_rounds, max_concurrency, evidence_target, include_all_evidence)

    @mcp.tool()
    def agentweb_parallel_research(tasks: list[str], mode: ResearchMode = "focus", max_concurrency: int = 4, max_rounds: int | None = None, evidence_target: int | None = None, include_all_evidence: bool = False) -> dict:
        """Run independent adaptive research tasks concurrently; each result is compact and answer-first."""
        return tools.parallel_research(tasks, mode, max_concurrency, max_rounds, evidence_target, include_all_evidence)

    @mcp.tool()
    def agentweb_extract_page(url: str, requested_schema: dict | None = None) -> dict:
        """Extract structured, trust-checked content from one public HTTP(S) URL."""
        return tools.extract_page(url, requested_schema)

    @mcp.tool()
    def agentweb_crawl(url: str, max_pages: int = 10, depth: int = 1, url_pattern: str | None = None) -> dict:
        """Crawl a bounded same-origin public site and return page metadata."""
        return tools.crawl(url, max_pages, depth, url_pattern)

    @mcp.tool()
    def agentweb_browser_open(url: str, actions: list[dict] | None = None) -> dict:
        """Open a public page through the isolated browser adapter with bounded actions."""
        return tools.browser_open(url, actions)

    @mcp.tool()
    def agentweb_create_monitor(task: str, frequency: MonitorFrequency = "daily", webhook_url: str | None = None, change_policy: dict | None = None) -> dict:
        """Create a durable monitor for a public URL or task."""
        return tools.create_monitor(task, frequency, webhook_url, change_policy)

    @mcp.tool()
    def agentweb_check_monitor(monitor_id: str) -> dict:
        """Run one check for an existing monitor and return its change status."""
        return tools.check_monitor(monitor_id)

    @mcp.tool()
    def agentweb_list_monitors() -> list[dict]:
        """List monitors without returning credential or session state."""
        return tools.list_monitors()

    @mcp.tool()
    def agentweb_create_plan(task: str, mode: ResearchMode | None = None, skill: str | None = None, inputs: dict | None = None) -> dict:
        """Create a reusable, sanitized retrieval plan before execution."""
        return tools.create_plan(task, mode, skill, inputs)

    @mcp.tool()
    def agentweb_execute_plan(plan_id: str, output_format: str | None = None) -> dict:
        """Execute a previously created, organization-scoped retrieval plan."""
        return tools.execute_plan(plan_id, output_format)

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the model-agnostic AgentWeb MCP server.")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind address when using streamable-http.")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port when using streamable-http.")
    parser.add_argument("--data", default="agentweb.sqlite3", help="SQLite database path for AgentWeb state.")
    args = parser.parse_args()
    mcp = create_mcp_server(AgentWebEngine(MemoryStore(args.data)))
    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport="streamable-http", host=args.host, port=args.port, streamable_http_path="/mcp")


if __name__ == "__main__":
    main()
