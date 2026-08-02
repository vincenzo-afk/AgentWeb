# Auth Setup

AgentWeb uses API keys for authentication.

1. Generate a key from your account/organization dashboard.
2. Store it as an environment variable rather than hardcoding it:

```bash
export AGENTWEB_API_KEY="sk-..."
```

3. Pass it via the `Authorization: Bearer` header on REST calls, or configure it in the SDK client:

```js
import { AgentWeb } from "@agentweb/sdk";

const internet = new AgentWeb({ apiKey: process.env.AGENTWEB_API_KEY });
```

```python
from agentweb import AgentWeb

internet = AgentWeb(api_key=os.environ["AGENTWEB_API_KEY"])
```

See [api/authentication.md](../api/authentication.md) for key scoping, rotation, and organization-level access controls, and [security/secrets-management.md](../security/secrets-management.md) for handling recommendations in production.

Next: [Quickstart](quickstart.md).
