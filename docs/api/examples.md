# API Examples

## Grounded research

```bash
curl https://api.agentweb.dev/v1/solve \
  -H "Authorization: Bearer $AGENTWEB_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task": "Find the cheapest RTX 6090 currently available in India and cite trustworthy sources"}'
```

## Monitoring

```bash
curl https://api.agentweb.dev/v1/observe \
  -H "Authorization: Bearer $AGENTWEB_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task": "Track visa slot availability and alert when a new slot appears", "webhook_url": "https://myapp.example.com/webhooks/agentweb"}'
```

## Comparison / multi-source research

```bash
curl https://api.agentweb.dev/v1/solve \
  -H "Authorization: Bearer $AGENTWEB_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task": "Compare AI startups competing with Company X that raised funding this month and released a new GitHub project", "mode": "dive"}'
```

More end-to-end examples with full source code live under [examples/](../../examples/README.md).
