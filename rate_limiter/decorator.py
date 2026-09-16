"""Decorator for wrapping a function call with rate limiting."""

import functools
from typing import Callable


class RateLimitExceeded(Exception):
    """Raised by @rate_limited when a call is rejected (429-style)."""

    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Rate limit exceeded for key={key!r}")


def rate_limited(limiter, key_fn: Callable[..., str] = None):
    """Decorate a function so calls are gated by ``limiter.allow(key)``.

    ``limiter`` must implement the common ``allow(key: str) -> bool``
    interface (TokenBucket, FixedWindowCounter, SlidingWindowLog, ...).

    ``key_fn`` optionally derives the rate-limit key from the call
    arguments (e.g. per-user limiting). It defaults to a constant key,
    meaning the whole function shares one limit bucket.

    Raises RateLimitExceeded when the call is rejected, mirroring an
    HTTP 429 response in a web server context.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = key_fn(*args, **kwargs) if key_fn else "default"
            if not limiter.allow(key):
                raise RateLimitExceeded(key)
            return func(*args, **kwargs)

        return wrapper

    return decorator
