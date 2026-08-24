# Learning loop

AgentWeb records bounded outcome signals to improve operational visibility without storing task text, page content, credentials, or prompts. Every completed solve records the selected strategy (`skill` or planner intent), mode, success classification, evidence score, execution ID, and latency. Clients may also submit explicit outcome feedback when an operator or downstream evaluator has a stronger label.

## Record explicit feedback

```http
POST /v1/learning/outcomes
Content-Type: application/json
Idempotency-Key: evaluator-001

{
  "strategy": "comparison",
  "mode": "focus",
  "success": true,
  "evidence_score": 0.92,
  "execution_id": "exec_123",
  "latency_ms": 840
}
```

The `strategy` identifier is bounded to 120 characters, `evidence_score` must be between 0 and 1, and latency is bounded to one day in milliseconds. The endpoint requires `learning:write`; it intentionally does not accept a raw task or arbitrary content field.

## Read aggregate summaries

```http
GET /v1/learning/summary?limit=50
```

The response groups observations by strategy and mode and returns observation count, success rate, average evidence score, average latency, and the most recent observation time. Results are organization-scoped and require `learning:read`.

The initial implementation is a privacy-safe local learning loop. It provides durable feedback signals and summaries; it does not autonomously rewrite skills, change safety policy, or deploy a managed machine-learning model.
