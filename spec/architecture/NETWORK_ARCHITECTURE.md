# Network Architecture

## Network zones

- **Public ingress** — API tier only, TLS-terminated, authenticated.
- **Internal service mesh** — API tier, orchestration tier, and stores communicate over an internal network, not publicly reachable.
- **Egress zone (execution workers)** — Search/Crawl/Browser/Extract workers are the only components permitted outbound access to the open internet, since they're the components that must reach third-party sites. This isolates the blast radius of any compromise via a malicious page — see [../security/SECURITY_MODEL.md](../security/SECURITY_MODEL.md) and [../../docs/security/sandboxing.md](../../docs/security/sandboxing.md).
- **Webhook egress** — a separate, rate-limited egress path for delivering signed webhook payloads to customer endpoints ([../../docs/api/webhooks.md](../../docs/api/webhooks.md)).

No component outside the egress zone should have direct outbound internet access; this constraint should be enforced at the network policy level, not just by convention.
