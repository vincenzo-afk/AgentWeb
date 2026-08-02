# Trust and Safety

Distinct from the per-source [Ranking](ranking.md) mechanism, this covers platform-level safety controls: what AgentWeb will and won't fetch, browse, or surface.

## Controls

- Respecting `robots.txt` and site terms where applicable for crawling/browsing.
- Refusing to browse or extract from sources associated with malware distribution, phishing, or other clearly harmful content.
- Rate-limiting outbound requests per target to avoid abusive load on third-party sites.
- Filtering synthesis output to avoid surfacing content that violates AgentWeb's usage policies (e.g., content facilitating illegal activity).

## Relationship to trust scoring

Trust and safety controls operate as a gate (should this source be touched/used at all), while the [Trust Model](../concepts/trust-model.md) operates as a ranking signal (how much should this source be weighted). See also [security/threat-model.md](../security/threat-model.md).
