"""Durable SQLite-backed monitor scheduler."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from .auth import RateLimiter
from .memory import MemoryStore
from .models import Monitor


class Scheduler:
    """Execute due monitor jobs without creating an implicit daemon in the API process."""

    def __init__(
        self,
        store: MemoryStore,
        checker: Callable[[Monitor], Monitor],
        *,
        lease_seconds: float = 120.0,
        poll_seconds: float = 1.0,
    ) -> None:
        self.store = store
        self.checker = checker
        self.lease_seconds = lease_seconds
        self.poll_seconds = poll_seconds
        self.scheduled_limiter = RateLimiter(capacity=100.0, refill_per_second=100.0 / 3600.0)

    def run_once(self, now: float | None = None) -> dict[str, Any] | None:
        """Claim and execute the highest-priority due job; return None when no job is due."""
        current = time.time() if now is None else now
        job = self.store.claim_due_job(current, self.lease_seconds)
        if not job:
            return None
        monitor_id = job.get("monitor_id")
        org_id = str(job.get("org_id") or "development")
        monitor = self.store.get_monitor(monitor_id, org_id) if monitor_id else None
        if not monitor or monitor.status != "active":
            self.store.cancel_job(job["id"], org_id)
            return {"job_id": job["id"], "status": "skipped", "reason": "monitor is unavailable or inactive"}
        try:
            self.scheduled_limiter.check(org_id, 1.0, bucket="scheduled")
            checked = self.checker(monitor)
            self.store.acknowledge_job(job["id"], checked.frequency, current, org_id)
            return {
                "job_id": job["id"],
                "monitor_id": checked.id,
                "status": "succeeded",
                "event": checked.last_event,
                "monitor": checked.to_dict(),
            }
        except Exception as error:  # noqa: BLE001 - job boundary must preserve the queue
            job_status = self.store.fail_job(job["id"], str(error), current, org_id)
            return {
                "job_id": job["id"],
                "monitor_id": monitor.id,
                "status": job_status,
                "error": str(error),
            }

    def run_forever(self, stop_event: threading.Event | None = None) -> None:
        """Run until the caller sets the stop event or sends an interrupt to the process."""
        stop_event = stop_event or threading.Event()
        while not stop_event.is_set():
            result = self.run_once()
            if result is None:
                stop_event.wait(self.poll_seconds)
