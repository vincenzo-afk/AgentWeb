# Rate Limits

See [docs/api/rate-limits.md](../../docs/api/rate-limits.md) for usage-facing documentation. Build-level contract: limits are enforced via a token-bucket per API key, partitioned by cost-weight (deeper [modes](../../docs/concepts/retrieval-modes.md) consume more tokens per call). Bucket state is checked before orchestration begins so rejected requests don't consume execution resources. Monitor checks draw from a separate scheduled-execution bucket, not the interactive request bucket.
