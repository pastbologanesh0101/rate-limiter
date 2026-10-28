import threading
import time

from .base import Limiter


class FixedWindow(Limiter):
    """Fixed window counter: allows up to `limit` requests per
    `window_seconds`-wide window. Simple and cheap, but allows up to 2x
    `limit` requests near a window boundary (burst at the edge)."""

    def __init__(self, limit: int, window_seconds: float, *, clock=time.monotonic):
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._limit = limit
        self._window = float(window_seconds)
        self._clock = clock
        self._window_start = clock()
        self._count = 0
        self._lock = threading.Lock()

    def allow(self, n: int = 1) -> bool:
        with self._lock:
            now = self._clock()
            if now - self._window_start >= self._window:
                self._window_start = now
                self._count = 0

            if self._count + n <= self._limit:
                self._count += n
                return True
            return False
