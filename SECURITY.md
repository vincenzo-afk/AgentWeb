# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in AgentWeb, please report it privately rather than opening a public issue. Email the security contact listed in [SUPPORT.md](SUPPORT.md) with:

- A description of the vulnerability and its potential impact
- Steps to reproduce, including any proof-of-concept code
- The affected component (API, browser execution layer, memory store, graph store, SDKs, etc.)

We aim to acknowledge reports within a few business days and to provide a remediation timeline once the issue is triaged.

## Supported Versions

Security fixes are applied to the latest major release. Older versions may receive fixes at the maintainers' discretion depending on severity.

## Scope

Areas of particular sensitivity given AgentWeb's architecture:

- **Browser execution layer** — sandboxing of headless browser sessions, since these execute against arbitrary third-party pages (see [docs/security/sandboxing.md](docs/security/sandboxing.md)).
- **Credential and API key handling** — see [docs/security/secrets-management.md](docs/security/secrets-management.md).
- **Memory and graph storage** — snapshots and extracted data may contain sensitive third-party content; see [docs/security/data-privacy.md](docs/security/data-privacy.md).
- **Webhook delivery** for monitoring alerts — signature verification and replay protection.

## Disclosure

We follow coordinated disclosure. Please give us a reasonable window to fix a reported issue before any public disclosure.
