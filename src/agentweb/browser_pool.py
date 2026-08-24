from __future__ import annotations

import multiprocessing
import threading
from typing import Any

from .errors import AgentWebError, BrowserActionError, BrowserTimeoutError


def _run_browser_session(payload: dict[str, Any]):
    """Entry point for a spawned worker; imports the browser engine lazily to avoid cycles."""
    from .browser import BrowserEngine
    from .trust_engine import TrustEngine

    engine = BrowserEngine(
        trust_engine=TrustEngine(set(payload.get("blocked_domains", []))),
        executable_path=payload.get("executable_path"),
        action_timeout=float(payload["action_timeout"]),
        session_timeout=float(payload["session_timeout"]),
        allow_cross_origin=bool(payload["allow_cross_origin"]),
        max_workers=1,
        process_workers=0,
    )
    return engine._open_in_process(payload["url"], payload.get("actions"), payload.get("credential"))


class BrowserProcessPool:
    """Lazy, bounded process pool for browser sessions with explicit shutdown."""

    def __init__(self, workers: int, *, start_method: str | None = None) -> None:
        self.workers = max(1, min(int(workers), 8))
        method = start_method or "spawn"
        self._context = multiprocessing.get_context(method)
        self._pool: multiprocessing.pool.Pool | None = None
        self._lock = threading.Lock()

    def _get_pool(self):
        with self._lock:
            if self._pool is None:
                self._pool = self._context.Pool(processes=self.workers, maxtasksperchild=50)
            return self._pool

    def run(self, payload: dict[str, Any], timeout: float):
        pool = self._get_pool()
        result = pool.apply_async(_run_browser_session, (payload,))
        try:
            return result.get(timeout=max(0.1, timeout))
        except multiprocessing.TimeoutError as error:
            self.restart()
            raise BrowserTimeoutError("browser worker process exceeded the session timeout") from error
        except Exception as error:
            if isinstance(error, AgentWebError):
                raise
            raise BrowserActionError(str(error)) from error

    def restart(self) -> None:
        with self._lock:
            pool, self._pool = self._pool, None
        if pool is not None:
            pool.terminate()
            pool.join()

    def close(self) -> None:
        with self._lock:
            pool, self._pool = self._pool, None
        if pool is not None:
            pool.close()
            pool.join()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self.close()
