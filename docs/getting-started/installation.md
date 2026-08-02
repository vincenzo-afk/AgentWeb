# Installation

AgentWeb can be used via REST directly, or through a language SDK.

## JavaScript / TypeScript

```bash
npm install @agentweb/sdk
```

## Python

```bash
pip install agentweb
```

## REST

No installation required — call the API directly:

```bash
curl https://api.agentweb.dev/v1/solve \
  -H "Authorization: Bearer $AGENTWEB_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task": "Find the cheapest RTX 6090 currently available in India"}'
```

See [SDK docs](../sdk/index.md) for full client library documentation, or [api/index.md](../api/index.md) for the raw REST reference.

Next: [Auth Setup](auth-setup.md).
