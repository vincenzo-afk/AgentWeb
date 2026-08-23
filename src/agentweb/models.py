"""Small, serializable data contracts for AgentWeb's Phase 0/1 API."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class Source:
    id: str
    url: str
    title: str = ""
    snippet: str = ""
    trust_score: float = 0.0
    cited: bool = True


@dataclass
class Citation:
    claim_span: list[int]
    source_ids: list[str]


@dataclass
class SolveResponse:
    execution_id: str
    mode: str
    answer: str
    sources: list[Source] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    insufficient_evidence: bool = False
    output_format: str = "text"
    evidence_score: float = 0.0
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    structured_output: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Monitor:
    id: str
    task: str
    status: str = "active"
    frequency: str = "daily"
    target_url: str | None = None
    webhook_url: str | None = None
    last_checked_at: str | None = None
    last_change_at: str | None = None
    last_event: str | None = None
    last_error: str | None = None
    org_id: str = "development"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
