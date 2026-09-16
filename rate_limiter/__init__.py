"""
rate_limiter - a small collection of classic rate limiting algorithms.

All limiters implement a common interface:

    limiter.allow(key: str) -> bool

and are thread-safe and clock-injectable (accept a ``time_fn`` callable,
defaulting to ``time.monotonic``) so they can be tested deterministically
without real sleeps.
"""

from .token_bucket import TokenBucket
from .fixed_window import FixedWindowCounter
from .sliding_window_log import SlidingWindowLog
from .decorator import rate_limited, RateLimitExceeded

__all__ = [
    "TokenBucket",
    "FixedWindowCounter",
    "SlidingWindowLog",
    "rate_limited",
    "RateLimitExceeded",
]
