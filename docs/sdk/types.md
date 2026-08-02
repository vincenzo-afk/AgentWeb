# Types

Core shared types across SDKs (shown here in TypeScript-flavored pseudocode; Python equivalents mirror these as typed dataclasses/TypedDicts).

```ts
type Mode = "flash" | "focus" | "dive" | "monitor";

interface SolveRequest {
  task: string;
  mode?: Mode;
  skill?: string;
  inputs?: Record<string, unknown>;
  webhookUrl?: string;
  idempotencyKey?: string;
}

interface Source {
  id: string;
  url: string;
  trustScore: number;
  cited: boolean;
}

interface Citation {
  claimSpan: [number, number];
  sourceIds: string[];
}

interface SolveResponse {
  executionId: string;
  mode: Mode;
  answer: string;
  sources: Source[];
  citations: Citation[];
  createdAt: string;
}

interface AgentWebError {
  type: string;
  message: string;
  requestId: string;
}
```

See [api/responses.md](../api/responses.md) and [api/citations.md](../api/citations.md) for the canonical response shape these types mirror.
