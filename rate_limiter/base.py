"""Common interface for all rate limiter implementations."""

from abc import ABC, abstractmethod


class BaseRateLimiter(ABC):
    """Abstract base class defining the shared rate limiter interface.

    Every concrete limiter must be:
      * thread-safe (internally protected with a lock)
      * clock-injectable (accept ``time_fn`` for deterministic testing)
      * keyed (``allow`` takes a ``key`` so a single limiter instance can
        track independent buckets/windows per client, user, IP, etc.)
    """

    @abstractmethod
    def allow(self, key: str) -> bool:
        """Return True if a request for ``key`` should be allowed now,
        False if it should be rejected (HTTP 429-style)."""
        raise NotImplementedError
