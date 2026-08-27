"""Model-agnostic MCP server exposing AgentWeb's bounded public capabilities."""
from __future__ import annotations

import argparse
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
            "media_support": {"youtube": "metadata and public captions when exposed", "generic_video": "OpenGraph media metadata", "credentials": "not accepted"},
            "excluded_self_hosted_or_keyed": ["see selfhosting.md"],
        }

    def research(self, task: str, mode: ResearchMode = "focus", max_rounds: int | None = None, max_concurrency: int | None = None, evidence_target: int | None = None, include_all_evidence: bool = True) -> dict:
        normalized_task = _bounded_text(task, field="task", maximum=2_000)
        try:
            try:
                response = self.engine.solve(normalized_task, mode=mode, output_format="text", max_rounds=max_rounds, max_concurrency=max_concurrency, evidence_target=evidence_target, include_all_evidence=include_all_evidence)
            except TypeError as error:
                if "unexpected keyword argument" not in str(error):
                    raise
                response = self.engine.solve(normalized_task, mode=mode, output_format="text")
            return response.to_dict()
        except Exception as error:
            return {"status": "failed", "error": str(error) or type(error).__name__, "error_type": type(error).__name__, "mode": mode}

    def parallel_research(self, tasks: list[str], mode: ResearchMode = "focus", max_concurrency: int = 4, max_rounds: int | None = None, evidence_target: int | None = None, include_all_evidence: bool = True) -> dict:
        if not isinstance(tasks, list) or not tasks or len(tasks) > 12:
            raise ValueError("tasks must contain between 1 and 12 items")
        normalized_tasks = [_bounded_text(task, field="task", maximum=2_000) for task in tasks]
        if isinstance(max_concurrency, bool) or not isinstance(max_concurrency, int) or not 1 <= max_concurrency <= 8:
            raise ValueError("max_concurrency must be an integer between 1 and 8")
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(max_concurrency, len(normalized_tasks))) as pool:
            results = list(pool.map(lambda task: self.research(task, mode, max_rounds, max_concurrency, evidence_target, include_all_evidence), normalized_tasks))
        return {"status": "complete", "mode": mode, "task_count": len(results), "results": results}

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
            "Use agentweb_parallel_research for separable subquestions. Do not infer facts beyond returned evidence; self-hosted and credentialed integrations are documented in selfhosting.md."
        ),
    )

    @mcp.tool()
    def agentweb_capabilities() -> dict:
        """List supported modes, public source branches, and excluded integrations."""
        return tools.capabilities()

    @mcp.tool()
    def agentweb_research(task: str, mode: ResearchMode = "focus", max_rounds: int | None = None, max_concurrency: int | None = None, evidence_target: int | None = None, include_all_evidence: bool = True) -> dict:
        """Run bounded adaptive research; it gathers parallel evidence and returns one consolidated result."""
        return tools.research(task, mode, max_rounds, max_concurrency, evidence_target, include_all_evidence)

    @mcp.tool()
    def agentweb_parallel_research(tasks: list[str], mode: ResearchMode = "focus", max_concurrency: int = 4, max_rounds: int | None = None, evidence_target: int | None = None, include_all_evidence: bool = True) -> dict:
        """Run independent adaptive research tasks concurrently and consolidate each result."""
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
