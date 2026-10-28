import threading
import time

from .base import Limiter


class LeakyBucket(Limiter):
    """Leaky bucket: requests fill a bucket of fixed `capacity` that drains
    at a constant `leak_rate` units/second. Smooths bursts into a steady
    output rate instead of allowing them through immediately."""

    def __init__(self, capacity: int, leak_rate: float, *, clock=time.monotonic):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if leak_rate <= 0:
            raise ValueError("leak_rate must be positive")
        self._capacity = float(capacity)
        self._level = 0.0
        self._leak_rate = float(leak_rate)
        self._clock = clock
        self._last_leak = clock()
        self._lock = threading.Lock()

    def allow(self, n: int = 1) -> bool:
        with self._lock:
            now = self._clock()
            elapsed = now - self._last_leak
            if elapsed > 0:
                self._level = max(0.0, self._level - elapsed * self._leak_rate)
                self._last_leak = now

            if self._level + n <= self._capacity:
                self._level += n
                return True
            return False
