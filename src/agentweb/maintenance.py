"""Explicit maintenance operations for local retention and privacy lifecycle controls."""

from __future__ import annotations

from typing import Any

from .auth import KeyStore
from .memory import MemoryStore
from .metrics import MetricsRegistry
from .trace import TraceStore


def purge_retention(
    memory: MemoryStore,
    traces: TraceStore,
    *,
    snapshot_retention_days: int = 90,
    crawl_retention_days: int = 90,
    trace_retention_days: int = 30,
    metric_retention_days: int = 30,
    audit_retention_days: int = 730,
    org_id: str | None = None,
    now: float | None = None,
    metrics: MetricsRegistry | None = None,
    audit_store: KeyStore | None = None,
) -> dict[str, Any]:
    """Delete only expired local records and report exact counts."""
    if snapshot_retention_days < 0 or crawl_retention_days < 0 or trace_retention_days < 0 or metric_retention_days < 0 or audit_retention_days < 0:
        raise ValueError("retention days cannot be negative")
    deleted_snapshots = memory.purge_expired_snapshots(
        snapshot_retention_days * 86_400,
        now=now,
        org_id=org_id,
    )
    deleted_crawls = memory.purge_expired_crawls(
        crawl_retention_days * 86_400,
        now=now,
        org_id=org_id,
    )
    deleted_traces = traces.purge_expired(
        trace_retention_days * 86_400,
        now=now,
        org_id=org_id,
    )
    deleted_metrics = metrics.purge_expired(metric_retention_days * 86_400, now=now, org_id=org_id) if metrics else 0
    deleted_audit = audit_store.purge_expired_audit(audit_retention_days * 86_400, now=now, org_id=org_id) if audit_store else 0
    return {
        "org_id": org_id,
        "snapshot_retention_days": snapshot_retention_days,
        "crawl_retention_days": crawl_retention_days,
        "trace_retention_days": trace_retention_days,
        "metric_retention_days": metric_retention_days,
        "audit_retention_days": audit_retention_days,
        "deleted_snapshots": deleted_snapshots,
        "deleted_crawls": deleted_crawls,
        "deleted_traces": deleted_traces,
        "deleted_metrics": deleted_metrics,
        "deleted_audit": deleted_audit,
    }
