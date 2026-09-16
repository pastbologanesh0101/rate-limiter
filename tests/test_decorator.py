import unittest

from rate_limiter import FixedWindowCounter, rate_limited, RateLimitExceeded


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestRateLimitedDecorator(unittest.TestCase):
    def test_allows_calls_up_to_limit(self):
        clock = FakeClock()
        limiter = FixedWindowCounter(limit=3, window_seconds=10.0, time_fn=clock)

        @rate_limited(limiter)
        def handler():
            return "ok"

        for _ in range(3):
            self.assertEqual(handler(), "ok")

    def test_raises_rate_limit_exceeded_over_limit(self):
        clock = FakeClock()
        limiter = FixedWindowCounter(limit=2, window_seconds=10.0, time_fn=clock)

        @rate_limited(limiter)
        def handler():
            return "ok"

        handler()
        handler()
        with self.assertRaises(RateLimitExceeded):
            handler()

    def test_key_fn_creates_independent_limits_per_argument(self):
        clock = FakeClock()
        limiter = FixedWindowCounter(limit=1, window_seconds=10.0, time_fn=clock)

        @rate_limited(limiter, key_fn=lambda user: user)
        def handler(user):
            return f"handled {user}"

        self.assertEqual(handler("alice"), "handled alice")
        with self.assertRaises(RateLimitExceeded):
            handler("alice")
        # bob has his own bucket
        self.assertEqual(handler("bob"), "handled bob")


if __name__ == "__main__":
    unittest.main()
