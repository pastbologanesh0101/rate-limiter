#!/usr/bin/env python3
"""Demo: fire a burst of requests at each rate limiter and report results.

Run with:  python demo.py
"""

from rate_limiter import TokenBucket, FixedWindowCounter, SlidingWindowLog
from rate_limiter.decorator import rate_limited, RateLimitExceeded


class FakeClock:
    """A controllable fake clock used so the demo runs instantly, with no
    real sleeping, while still exercising window/refill behavior."""

    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def run_burst(limiter, key: str, n: int) -> tuple[int, int]:
    allowed = 0
    rejected = 0
    for _ in range(n):
        if limiter.allow(key):
            allowed += 1
        else:
            rejected += 1
    return allowed, rejected


def demo_token_bucket() -> None:
    print("\n=== Token Bucket (capacity=5, refill_rate=1/s) ===")
    clock = FakeClock()
    limiter = TokenBucket(capacity=5, refill_rate=1.0, time_fn=clock)

    allowed, rejected = run_burst(limiter, "user-1", 10)
    print(f"Initial burst of 10 requests -> allowed={allowed}, rejected={rejected}")

    print("Advancing fake clock by 3 seconds (refills 3 tokens)...")
    clock.advance(3.0)
    allowed, rejected = run_burst(limiter, "user-1", 10)
    print(f"Next burst of 10 requests   -> allowed={allowed}, rejected={rejected}")


def demo_fixed_window() -> None:
    print("\n=== Fixed Window Counter (limit=5, window=10s) ===")
    clock = FakeClock()
    limiter = FixedWindowCounter(limit=5, window_seconds=10.0, time_fn=clock)

    allowed, rejected = run_burst(limiter, "user-1", 10)
    print(f"Burst of 10 requests in window 1 -> allowed={allowed}, rejected={rejected}")

    print("Advancing fake clock by 10 seconds (new window)...")
    clock.advance(10.0)
    allowed, rejected = run_burst(limiter, "user-1", 10)
    print(f"Burst of 10 requests in window 2 -> allowed={allowed}, rejected={rejected}")


def demo_sliding_window_log() -> None:
    print("\n=== Sliding Window Log (limit=5, window=10s) ===")
    clock = FakeClock()
    limiter = SlidingWindowLog(limit=5, window_seconds=10.0, time_fn=clock)

    allowed, rejected = run_burst(limiter, "user-1", 10)
    print(f"Burst of 10 requests -> allowed={allowed}, rejected={rejected}")

    print("Advancing fake clock by 6 seconds (partial slide)...")
    clock.advance(6.0)
    allowed, rejected = run_burst(limiter, "user-1", 5)
    print(f"5 more requests      -> allowed={allowed}, rejected={rejected}")

    print("Advancing fake clock by 5 more seconds (old entries expire)...")
    clock.advance(5.0)
    allowed, rejected = run_burst(limiter, "user-1", 5)
    print(f"5 more requests      -> allowed={allowed}, rejected={rejected}")


def demo_decorator() -> None:
    print("\n=== @rate_limited decorator on a plain function ===")
    clock = FakeClock()
    limiter = FixedWindowCounter(limit=3, window_seconds=60.0, time_fn=clock)

    @rate_limited(limiter, key_fn=lambda user: user)
    def handle_request(user: str) -> str:
        return f"handled request for {user}"

    for i in range(5):
        try:
            print(f"  call {i + 1}: {handle_request('alice')}")
        except RateLimitExceeded as exc:
            print(f"  call {i + 1}: REJECTED (429) - {exc}")


if __name__ == "__main__":
    demo_token_bucket()
    demo_fixed_window()
    demo_sliding_window_log()
    demo_decorator()
