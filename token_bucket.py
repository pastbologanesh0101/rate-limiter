import threading
import time

from .base import Limiter


class TokenBucket(Limiter):
    """Classic token bucket: allows bursts up to `capacity`, refills at
    `refill_rate` tokens/second on average."""

    def __init__(self, capacity: int, refill_rate: float, *, clock=time.monotonic):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be positive")
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._refill_rate = float(refill_rate)
        self._clock = clock
        self._last_refill = clock()
        self._lock = threading.Lock()

    def allow(self, n: int = 1) -> bool:
        with self._lock:
            now = self._clock()
            elapsed = now - self._last_refill
            if elapsed > 0:
                self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
                self._last_refill = now

            if self._tokens >= n:
                self._tokens -= n
                return True
            return False
