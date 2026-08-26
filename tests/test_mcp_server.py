"""Contract tests for AgentWeb's model-agnostic MCP tool facade."""

from __future__ import annotations

import asyncio
import unittest

from mcp import Client
from agentweb.mcp_server import AgentWebMCPTools, create_mcp_server


class _Response:
    def to_dict(self) -> dict:
        return {"answer": "Grounded answer", "sources": [], "mode": "focus"}


class _Monitor:
    id = "mon_test"
    task = "Watch example.com"
    frequency = "daily"
    target_url = None
    status = "active"


class _Engine:
    def __init__(self) -> None:
        self.solve_calls: list[tuple[str, str, str]] = []
        self.extract_calls: list[str] = []
        self.monitor_calls: list[tuple[str, str]] = []

    def solve(self, task: str, mode: str, output_format: str) -> _Response:
        self.solve_calls.append((task, mode, output_format))
        return _Response()

    def extract(self, url: str) -> dict:
        self.extract_calls.append(url)
        return {"url": url, "title": "Example"}

    def create_monitor(self, task: str, frequency: str) -> _Monitor:
        self.monitor_calls.append((task, frequency))
        return _Monitor()


class MCPServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _Engine()
        self.tools = AgentWebMCPTools(self.engine)  # type: ignore[arg-type]

    def test_research_is_model_agnostic_and_uses_bounded_agentweb_inputs(self) -> None:
        result = self.tools.research("  Compare reliable public sources.  ", "dive")
        self.assertEqual(result["answer"], "Grounded answer")
        self.assertEqual(self.engine.solve_calls, [("Compare reliable public sources.", "dive", "text")])

    def test_extract_and_monitor_do_not_accept_external_credentials_or_webhooks(self) -> None:
        extract_result = self.tools.extract_page(" https://example.com ")
        monitor_result = self.tools.create_monitor("Watch example.com", "daily")
        self.assertEqual(extract_result["url"], "https://example.com")
        self.assertEqual(monitor_result["id"], "mon_test")
        self.assertEqual(self.engine.monitor_calls, [("Watch example.com", "daily")])

    def test_empty_or_oversized_tool_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.tools.research("", "focus")
        with self.assertRaises(ValueError):
            self.tools.extract_page("x" * 2_049)

    def test_server_factory_returns_a_protocol_server(self) -> None:
        server = create_mcp_server(self.engine)  # type: ignore[arg-type]
        self.assertEqual(server.name, "AgentWeb")

    def test_mcp_client_can_discover_and_call_the_research_tool(self) -> None:
        async def call_tool() -> str:
            server = create_mcp_server(self.engine)  # type: ignore[arg-type]
            async with Client(server) as client:
                available = await client.list_tools()
                self.assertIn("agentweb_research", [tool.name for tool in available.tools])
                result = await client.call_tool("agentweb_research", {"task": "Compare public sources.", "mode": "focus"})
                return "\n".join(getattr(item, "text", "") for item in result.content)

        result = asyncio.run(call_tool())
        self.assertIn("Grounded answer", result)


if __name__ == "__main__":
    unittest.main()
