import threading
from typing import Callable, Dict

from .base import Limiter


class PerKeyLimiter:
    """Lazily creates and holds one Limiter per key (e.g. client IP, user
    ID, API token) so a single factory can rate-limit many independent
    callers. The dict lock only guards limiter creation/lookup; the actual
    allow() check runs on that key's own limiter lock."""

    def __init__(self, factory: Callable[[], Limiter]):
        self._factory = factory
        self._limiters: Dict[str, Limiter] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, n: int = 1) -> bool:
        limiter = self._limiters.get(key)
        if limiter is None:
            with self._lock:
                limiter = self._limiters.get(key)
                if limiter is None:
                    limiter = self._factory()
                    self._limiters[key] = limiter
        return limiter.allow(n)

    def __len__(self) -> int:
        return len(self._limiters)
