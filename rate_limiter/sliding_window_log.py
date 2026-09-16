"""Sliding Window Log rate limiter.

Each key keeps a log (deque) of timestamps of its recent allowed requests.
On every call, timestamps older than ``window_seconds`` are evicted from the
front of the deque, then a request is allowed only if the remaining log is
shorter than ``limit``. This gives an exact sliding window with no boundary
burst problem, at the cost of O(limit) memory per key.
"""

import threading
import time
from collections import deque
from typing import Callable, Deque, Dict


class SlidingWindowLog:
    """Sliding window log rate limiter.

    Tradeoffs:
      * Exact: at any instant, at most ``limit`` requests are allowed in the
        trailing ``window_seconds`` -- no double-burst at window edges like
        fixed windows have.
      * Memory cost is O(limit) timestamps per key, which is higher than
        fixed window or token bucket.
      * Slightly more CPU work per call (evicting stale timestamps).
    """

    def __init__(
        self,
        limit: int,
        window_seconds: float,
        time_fn: Callable[[], float] = time.monotonic,
    ):
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.limit = limit
        self.window_seconds = float(window_seconds)
        self._time_fn = time_fn
        self._lock = threading.Lock()
        self._logs: Dict[str, Deque[float]] = {}

    def allow(self, key: str) -> bool:
        now = self._time_fn()
        cutoff = now - self.window_seconds
        with self._lock:
            log = self._logs.setdefault(key, deque())
            while log and log[0] <= cutoff:
                log.popleft()

            if len(log) < self.limit:
                log.append(now)
                return True
            return False

    def current_count(self, key: str) -> int:
        """Introspection helper, mainly useful for tests/demo."""
        now = self._time_fn()
        cutoff = now - self.window_seconds
        with self._lock:
            log = self._logs.get(key)
            if not log:
                return 0
            while log and log[0] <= cutoff:
                log.popleft()
            return len(log)
