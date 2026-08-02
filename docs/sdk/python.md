# Python SDK

## Install

```bash
pip install agentweb
```

## Usage

```python
import os
from agentweb import AgentWeb

internet = AgentWeb(api_key=os.environ["AGENTWEB_API_KEY"])

result = internet.solve(
    task="Find the cheapest RTX 6090 currently available in India and cite trustworthy sources"
)

monitor = internet.observe(
    task="Track visa slot availability and alert when a new slot appears",
    webhook_url="https://myapp.example.com/webhooks/agentweb"
)
```

## Async client

```python
from agentweb import AsyncAgentWeb

async def main():
    internet = AsyncAgentWeb(api_key=os.environ["AGENTWEB_API_KEY"])
    result = await internet.solve(task="...")
```

## Error handling

```python
from agentweb.errors import AgentWebError

try:
    internet.solve(task="...")
except AgentWebError as e:
    print(e.type, e.message, e.request_id)
```

See [api/errors.md](../api/errors.md) for the full error taxonomy.
