import threading
import time
from collections import deque

from .base import Limiter


class SlidingWindowLog(Limiter):
    """Sliding window log: keeps a timestamp per admitted request and only
    counts the ones inside the trailing `window_seconds`. Exact, but memory
    grows with request volume inside the window."""

    def __init__(self, limit: int, window_seconds: float, *, clock=time.monotonic):
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._limit = limit
        self._window = float(window_seconds)
        self._clock = clock
        self._log: deque = deque()
        self._lock = threading.Lock()

    def allow(self, n: int = 1) -> bool:
        with self._lock:
            now = self._clock()
            cutoff = now - self._window
            while self._log and self._log[0] < cutoff:
                self._log.popleft()

            if len(self._log) + n <= self._limit:
                for _ in range(n):
                    self._log.append(now)
                return True
            return False
