# REST

If no SDK exists for your language, call the API directly over HTTPS.

```bash
curl https://api.agentweb.dev/v1/solve \
  -H "Authorization: Bearer $AGENTWEB_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task": "Find the cheapest RTX 6090 currently available in India and cite trustworthy sources"}'
```

See [api/index.md](../api/index.md) for the full endpoint reference, [api/authentication.md](../api/authentication.md) for auth, and [openapi/openapi.yaml](../../openapi/openapi.yaml) for a machine-readable spec you can feed into most codegen tools to produce a client in any language.
