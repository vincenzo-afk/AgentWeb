"""Durable SQLite-backed monitor and webhook scheduler."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from .auth import RateLimiter
from .errors import RateLimitError
from .memory import MemoryStore
from .models import Monitor


class Scheduler:
    """Execute due jobs without creating an implicit daemon in the API process."""

    def __init__(
        self,
        store: MemoryStore,
        checker: Callable[[Monitor], Monitor],
        *,
        webhook_sender: Callable[[dict[str, Any]], Any] | None = None,
        lease_seconds: float = 120.0,
        poll_seconds: float = 1.0,
        coordinator: Any | None = None,
    ) -> None:
        self.store = store
        self.checker = checker
        self.webhook_sender = webhook_sender
        self.lease_seconds = lease_seconds
        self.poll_seconds = poll_seconds
        self.coordinator = coordinator
        self.scheduled_limiter = RateLimiter(capacity=100.0, refill_per_second=100.0 / 3600.0)
        self.webhook_limiter = RateLimiter(capacity=20.0, refill_per_second=20.0 / 60.0)

    @property
    def queue_store(self):
        return self.coordinator or self.store

    def _check_limit(self, org_id: str, bucket: str, local_limiter: RateLimiter, capacity: float, refill_per_second: float) -> None:
        if self.coordinator is not None:
            self.coordinator.consume_rate_limit(org_id, bucket, 1.0, capacity, refill_per_second)
        else:
            local_limiter.check(org_id, 1.0, bucket=bucket)

    @staticmethod
    def _webhook_retry_delay(attempt: int) -> float:
        # Five total attempts remain bounded within a 24-hour delivery window.
        return (300.0, 1_800.0, 7_200.0, 43_200.0)[max(0, min(attempt - 1, 3))]

    def _run_webhook(self, job: dict[str, Any], current: float, org_id: str) -> dict[str, Any]:
        delivery = self.store.get_webhook_delivery(job["id"], org_id)
        if not delivery:
            self.queue_store.cancel_job(job["id"], org_id, job.get("lease_token"))
            return {"job_id": job["id"], "status": "skipped", "reason": "delivery record is unavailable"}
        if delivery["status"] == "delivered" or delivery["already_delivered"]:
            self.store.mark_webhook_delivery(job["id"], org_id, "delivered", None, current)
            self.queue_store.cancel_job(job["id"], org_id, job.get("lease_token"))
            return {"job_id": job["id"], "status": "succeeded", "reason": "delivery already completed"}
        if self.webhook_sender is None:
            error = "webhook delivery worker is not configured"
            self.store.mark_webhook_delivery(job["id"], org_id, "dead_letter", error, current)
            status = self.queue_store.fail_job(job["id"], error, current, org_id, lease_token=job.get("lease_token"))
            return {"job_id": job["id"], "status": status, "error": error}
        try:
            self._check_limit(org_id, "webhook", self.webhook_limiter, 20.0, 20.0 / 60.0)
            result = self.webhook_sender(delivery)
            delivered = bool(getattr(result, "delivered", False))
            status_code = getattr(result, "status_code", None)
            error = getattr(result, "error", None)
            attempt = self.store.record_webhook_attempt(job["id"], org_id, delivered, status_code, error, current)
            if delivered:
                self.store.mark_webhook_delivery(job["id"], org_id, "delivered", None, current)
                self.queue_store.cancel_job(job["id"], org_id, job.get("lease_token"))
                return {"job_id": job["id"], "status": "succeeded", "attempt": attempt, "status_code": status_code}
            exhausted = attempt >= int(delivery["max_attempts"])
            delivery_status = "dead_letter" if exhausted else "retrying"
            self.store.mark_webhook_delivery(job["id"], org_id, delivery_status, error or "webhook delivery failed", current)
            job_status = self.queue_store.fail_job(
                job["id"], error or "webhook delivery failed", current, org_id,
                retry_delay=None if exhausted else self._webhook_retry_delay(attempt),
                lease_token=job.get("lease_token"),
            )
            return {"job_id": job["id"], "status": job_status, "attempt": attempt, "error": error or "webhook delivery failed"}
        except RateLimitError as error:
            message = str(error)[:500]
            exhausted = int(job.get("attempts", 1)) >= int(job.get("max_attempts", 5))
            delivery_status = "dead_letter" if exhausted else "rate_limited"
            self.store.mark_webhook_delivery(job["id"], org_id, delivery_status, message, current)
            job_status = self.queue_store.fail_job(
                job["id"], message, current, org_id,
                retry_delay=None if exhausted else float(error.retry_after or self._webhook_retry_delay(int(job.get("attempts", 1)))),
                lease_token=job.get("lease_token"),
            )
            return {"job_id": job["id"], "status": job_status, "error": message}
        except Exception as error:  # noqa: BLE001 - job boundary preserves the queue
            message = str(error)[:500]
            attempts = int(job.get("attempts", 1))
            exhausted = attempts >= int(job.get("max_attempts", 5))
            self.store.mark_webhook_delivery(job["id"], org_id, "dead_letter" if exhausted else "retrying", message, current)
            job_status = self.queue_store.fail_job(
                job["id"], message, current, org_id,
                retry_delay=None if exhausted else self._webhook_retry_delay(attempts),
                lease_token=job.get("lease_token"),
            )
            return {"job_id": job["id"], "status": job_status, "error": message}

    def run_once(self, now: float | None = None) -> dict[str, Any] | None:
        """Claim and execute the highest-priority due job; return None when no job is due."""
        current = time.time() if now is None else now
        job = self.queue_store.claim_due_job(current, self.lease_seconds)
        if not job:
            return None
        org_id = str(job.get("org_id") or "development")
        if job.get("job_type") == "webhook_delivery":
            return self._run_webhook(job, current, org_id)
        monitor_id = job.get("monitor_id")
        monitor = self.store.get_monitor(monitor_id, org_id) if monitor_id else None
        if not monitor or monitor.status != "active":
            self.queue_store.cancel_job(job["id"], org_id, job.get("lease_token"))
            return {"job_id": job["id"], "status": "skipped", "reason": "monitor is unavailable or inactive"}
        try:
            self._check_limit(org_id, "scheduled", self.scheduled_limiter, 100.0, 100.0 / 3600.0)
            checked = self.checker(monitor)
            self.queue_store.acknowledge_job(job["id"], checked.frequency, current, org_id, job.get("lease_token"))
            return {
                "job_id": job["id"],
                "monitor_id": checked.id,
                "status": "succeeded",
                "event": checked.last_event,
                "monitor": checked.to_dict(),
            }
        except RateLimitError as error:
            delay = float(error.retry_after or 1.0)
            job_status = self.queue_store.fail_job(job["id"], str(error), current, org_id, retry_delay=delay, lease_token=job.get("lease_token"))
            return {"job_id": job["id"], "monitor_id": monitor.id, "status": job_status, "error": str(error), "retry_after": delay}
        except Exception as error:  # noqa: BLE001 - job boundary must preserve the queue
            job_status = self.queue_store.fail_job(job["id"], str(error), current, org_id, lease_token=job.get("lease_token"))
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
