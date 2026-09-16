"""Token Bucket rate limiter.

Each key gets a bucket that holds up to ``capacity`` tokens. Tokens refill
continuously at ``refill_rate`` tokens/second. Each allowed request consumes
one token. This algorithm allows short bursts up to the bucket capacity
while enforcing a steady long-term average rate.
"""

import threading
import time
from typing import Callable, Dict


class _Bucket:
    __slots__ = ("tokens", "last_refill")

    def __init__(self, tokens: float, last_refill: float):
        self.tokens = tokens
        self.last_refill = last_refill


class TokenBucket:
    """Token bucket rate limiter.

    Tradeoffs:
      * Allows bursts up to ``capacity`` immediately, then throttles to the
        steady ``refill_rate``.
      * Smooth over time (no hard window edges), memory O(number of keys).
      * Slightly more complex to reason about than fixed windows since the
        "remaining budget" is continuous rather than a simple counter.
    """

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        time_fn: Callable[[], float] = time.monotonic,
    ):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be positive")
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self._time_fn = time_fn
        self._lock = threading.Lock()
        self._buckets: Dict[str, _Bucket] = {}

    def allow(self, key: str) -> bool:
        now = self._time_fn()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(self.capacity, now)
                self._buckets[key] = bucket

            elapsed = now - bucket.last_refill
            if elapsed > 0:
                bucket.tokens = min(
                    self.capacity, bucket.tokens + elapsed * self.refill_rate
                )
                bucket.last_refill = now

            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True
            return False

    def tokens_remaining(self, key: str) -> float:
        """Introspection helper, mainly useful for tests/demo."""
        with self._lock:
            bucket = self._buckets.get(key)
            return bucket.tokens if bucket else self.capacity
