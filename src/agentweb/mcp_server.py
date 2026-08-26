"""Model-agnostic MCP server exposing bounded AgentWeb research capabilities."""

from __future__ import annotations

import argparse
from typing import Literal

from mcp.server import MCPServer

from .engine import AgentWebEngine
from .memory import MemoryStore

ResearchMode = Literal["flash", "focus", "dive"]
MonitorFrequency = Literal["minutely", "hourly", "daily"]


def _bounded_text(value: str, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} must contain between 1 and {maximum} characters")
    return normalized


class AgentWebMCPTools:
    """Small tool facade that keeps MCP inputs independent from any calling model."""

    def __init__(self, engine: AgentWebEngine) -> None:
        self.engine = engine

    def research(self, task: str, mode: ResearchMode = "focus") -> dict:
        """Run grounded research and return AgentWeb's answer, source data, and evidence status."""
        response = self.engine.solve(_bounded_text(task, field="task", maximum=2_000), mode=mode, output_format="text")
        return response.to_dict()

    def extract_page(self, url: str) -> dict:
        """Extract a public page through AgentWeb's existing URL and trust-policy checks."""
        return self.engine.extract(_bounded_text(url, field="url", maximum=2_048))

    def create_monitor(self, task: str, frequency: MonitorFrequency = "daily") -> dict:
        """Create a bounded AgentWeb monitor without accepting caller-controlled webhooks or credentials."""
        monitor = self.engine.create_monitor(
            _bounded_text(task, field="task", maximum=2_000),
            frequency=frequency,
        )
        return {
            "id": monitor.id,
            "task": monitor.task,
            "frequency": monitor.frequency,
            "target_url": monitor.target_url,
            "status": monitor.status,
        }


def create_mcp_server(engine: AgentWebEngine | None = None) -> MCPServer:
    """Create the MCP server without starting a transport, enabling embedded tests."""
    tools = AgentWebMCPTools(engine or AgentWebEngine())
    mcp = MCPServer(
        "AgentWeb",
        instructions=(
            "Use AgentWeb for bounded, citation-oriented web research and public-page extraction. "
            "Do not infer facts beyond returned evidence. Monitoring creates a local AgentWeb monitor only."
        ),
    )

    @mcp.tool()
    def agentweb_research(task: str, mode: ResearchMode = "focus") -> dict:
        """Research a question with AgentWeb's flash, focus, or dive retrieval modes."""
        return tools.research(task, mode)

    @mcp.tool()
    def agentweb_extract_page(url: str) -> dict:
        """Extract structured, trust-checked content from one public HTTP(S) URL."""
        return tools.extract_page(url)

    @mcp.tool()
    def agentweb_create_monitor(task: str, frequency: MonitorFrequency = "daily") -> dict:
        """Create a local monitor for a question or public URL; webhook delivery is intentionally unavailable through MCP."""
        return tools.create_monitor(task, frequency)

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
