# AgentWeb MCP Server

AgentWeb exposes **model-agnostic** MCP tools. Claude, or another MCP-capable host, supplies the language model while AgentWeb supplies grounded research, public-page extraction, and local monitor creation. The MCP server has no Groq dependency and does not require any model-provider credential.

| Tool | Purpose | Boundaries |
|---|---|---|
| `agentweb_research` | Runs `flash`, `focus`, or `dive` grounded research. | Task is limited to 2,000 characters; AgentWeb returns its evidence status and citations. |
| `agentweb_extract_page` | Extracts a public HTTP(S) page. | URL is limited to 2,048 characters and is checked by AgentWeb’s existing trust policy. |
| `agentweb_create_monitor` | Creates a local monitor. | Caller cannot set webhooks, browser credentials, or service secrets. |

## Local Claude Desktop test

Install AgentWeb in the environment Claude Desktop will use, then add the following entry to `claude_desktop_config.json` and restart Claude Desktop:

```json
{
  "mcpServers": {
    "agentweb": {
      "command": "agentweb-mcp",
      "args": ["--data", "/absolute/path/to/agentweb.sqlite3"]
    }
  }
}
```

This starts the MCP server through `stdio`. It has no HTTP endpoint and needs no key because Claude Desktop starts the process on the same machine.

## Remote endpoint for Claude custom connectors

Run the server with Streamable HTTP when deploying it behind a public HTTPS reverse proxy:

```bash
agentweb-mcp --transport streamable-http --host 0.0.0.0 --port 8000 --data /srv/agentweb/agentweb.sqlite3
```

The endpoint is `https://<your-public-domain>/mcp`. Claude custom connectors reach remote MCP servers from Anthropic’s cloud infrastructure, so a private `localhost` address is not sufficient. A real public deployment should add OAuth before exposing write-capable monitor operations. For a temporary functional test, use the local Claude Desktop configuration above.

## Verification

Run the package tests with:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

The MCP Python SDK supports both `stdio` and Streamable HTTP transports; Streamable HTTP is the modern remote transport.[1]

## References

[1]: https://py.sdk.modelcontextprotocol.io/run/ "Running your server — MCP Python SDK"
