# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a security vulnerability. Use GitHub's private vulnerability-reporting workflow from the repository **Security** tab when it is available. If that workflow is unavailable, contact the repository owner through [vincenzo-afk's GitHub profile](https://github.com/vincenzo-afk) and request a private reporting channel.

Include a concise description, impact, reproduction steps, affected commit or file, and any safe proof of concept. Remove API keys, cookies, access tokens, private URLs, and private page contents from the report.

## Supported versions

The current `main` branch and the latest tagged release, when one exists, are the supported targets for security fixes. Older revisions may require an upgrade before a fix can be applied.

## Security-sensitive areas

The current MVP accepts arbitrary HTTP(S) URLs, reads public page content, stores normalized snapshots in SQLite, and optionally authenticates requests with a bearer token. Reviewers should pay particular attention to URL validation, response-size and timeout limits, untrusted HTML handling, secret exposure, local database permissions, and API authentication.

The broader architecture documents additional future areas, including browser execution, graph storage, and webhook delivery. Those components are not implemented in the current MVP and should not be treated as active attack surfaces in this version.

## Disclosure

Please allow maintainers reasonable time to investigate and address a report before public disclosure. Do not test against systems or data that you do not own or have permission to access.
