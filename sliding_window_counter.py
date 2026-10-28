import threading
import time

from .base import Limiter


class SlidingWindowCounter(Limiter):
    """Sliding window counter: approximates the sliding window log using two
    fixed-window counters (previous and current) blended by how far into the
    current window we are. O(1) memory, small approximation error, and the
    usual choice in production rate limiters (e.g. Cloudflare's)."""

    def __init__(self, limit: int, window_seconds: float, *, clock=time.monotonic):
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._limit = limit
        self._window = float(window_seconds)
        self._clock = clock
        self._curr_start = clock()
        self._curr_count = 0
        self._prev_count = 0
        self._lock = threading.Lock()

    def allow(self, n: int = 1) -> bool:
        with self._lock:
            now = self._clock()
            elapsed = now - self._curr_start

            if elapsed >= self._window:
                windows_passed = int(elapsed // self._window)
                self._prev_count = self._curr_count if windows_passed == 1 else 0
                self._curr_count = 0
                self._curr_start += windows_passed * self._window
                elapsed = now - self._curr_start

            weight = (self._window - elapsed) / self._window
            estimate = self._prev_count * weight + self._curr_count

            if estimate + n <= self._limit:
                self._curr_count += n
                return True
            return False
