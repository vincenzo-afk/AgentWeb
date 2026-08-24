# REST API

Base URL: `https://api.agentweb.dev/v1`. Full endpoint table: [docs/api/endpoints.md](../../docs/api/endpoints.md). Build-level requirements:

- All endpoints synchronous except `dive`-mode `solve` and all `observe` operations, which are async-capable via `webhook_url`.
- All mutating endpoints (`POST`/`DELETE`) support [idempotency keys](../../docs/api/idempotency.md).
- All list endpoints use cursor pagination ([docs/api/pagination.md](../../docs/api/pagination.md)).
- Successful JSON object responses share additive response metadata in a reserved `_meta` object and the `X-AgentWeb-API-Version` header; endpoint-specific fields remain at their documented top-level locations. `204 No Content` responses remain bodyless. Error shape is consistent across all endpoints — see [RESPONSE_SCHEMA.md](RESPONSE_SCHEMA.md) and [ERROR_CODES.md](ERROR_CODES.md).
