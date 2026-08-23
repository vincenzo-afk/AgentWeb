"""Conservative trust and safety gates for outbound URL access."""

from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str | None = None


class TrustEngine:
    """Perform local safety checks before the fetch adapter touches a URL."""

    def __init__(self, blocked_domains: set[str] | None = None) -> None:
        self.blocked_domains = {domain.lower().strip(".") for domain in (blocked_domains or set())}

    def should_fetch(self, url: str) -> GateDecision:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return GateDecision(False, "only absolute http and https URLs are allowed")
        host = parsed.hostname.lower().strip(".")
        if host in self.blocked_domains or any(host.endswith("." + domain) for domain in self.blocked_domains):
            return GateDecision(False, "target domain is blocked by the trust engine")
        try:
            address = ipaddress.ip_address(host)
            private_target = address.is_private or address.is_loopback or address.is_link_local or address.is_reserved
            if private_target and os.getenv("AGENTWEB_ALLOW_PRIVATE_TARGETS") != "1":
                return GateDecision(False, "private, loopback, link-local, or reserved IP targets are blocked")
        except ValueError:
            pass
        return GateDecision(True)

    def should_surface(self, content: str) -> GateDecision:
        if not content.strip():
            return GateDecision(False, "empty content cannot support a grounded result")
        return GateDecision(True)
