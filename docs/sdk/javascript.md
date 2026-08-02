# JavaScript / TypeScript SDK

## Install

```bash
npm install @agentweb/sdk
```

## Usage

```ts
import { AgentWeb } from "@agentweb/sdk";

const internet = new AgentWeb({ apiKey: process.env.AGENTWEB_API_KEY });

const result = await internet.solve({
  task: "Find the cheapest RTX 6090 currently available in India and cite trustworthy sources"
});

const monitor = await internet.observe({
  task: "Track visa slot availability and alert when a new slot appears",
  webhookUrl: "https://myapp.example.com/webhooks/agentweb"
});
```

## TypeScript types

Full request/response types are exported from the package root — see [types.md](types.md).

## Error handling

```ts
try {
  await internet.solve({ task: "..." });
} catch (err) {
  if (err instanceof AgentWebError) {
    console.error(err.type, err.message, err.requestId);
  }
}
```

See [api/errors.md](../api/errors.md) for the full error taxonomy.
