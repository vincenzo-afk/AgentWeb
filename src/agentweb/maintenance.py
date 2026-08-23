"""Explicit maintenance operations for local retention and privacy lifecycle controls."""

from __future__ import annotations

from typing import Any

from .memory import MemoryStore
from .trace import TraceStore


def purge_retention(
    memory: MemoryStore,
    traces: TraceStore,
    *,
    snapshot_retention_days: int = 90,
    trace_retention_days: int = 30,
    org_id: str | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Delete only expired tenant-owned snapshots and traces and report exact counts."""
    if snapshot_retention_days < 0 or trace_retention_days < 0:
        raise ValueError("retention days cannot be negative")
    deleted_snapshots = memory.purge_expired_snapshots(
        snapshot_retention_days * 86_400,
        now=now,
        org_id=org_id,
    )
    deleted_traces = traces.purge_expired(
        trace_retention_days * 86_400,
        now=now,
        org_id=org_id,
    )
    return {
        "org_id": org_id,
        "snapshot_retention_days": snapshot_retention_days,
        "trace_retention_days": trace_retention_days,
        "deleted_snapshots": deleted_snapshots,
        "deleted_traces": deleted_traces,
    }
