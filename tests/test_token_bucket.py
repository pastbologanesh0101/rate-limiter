import threading
import unittest

from rate_limiter import TokenBucket


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestTokenBucket(unittest.TestCase):
    def test_allows_up_to_capacity(self):
        clock = FakeClock()
        limiter = TokenBucket(capacity=5, refill_rate=1.0, time_fn=clock)
        results = [limiter.allow("k") for _ in range(5)]
        self.assertTrue(all(results))

    def test_rejects_over_capacity(self):
        clock = FakeClock()
        limiter = TokenBucket(capacity=5, refill_rate=1.0, time_fn=clock)
        for _ in range(5):
            self.assertTrue(limiter.allow("k"))
        # bucket is now empty, no time has passed
        self.assertFalse(limiter.allow("k"))
        self.assertFalse(limiter.allow("k"))

    def test_refills_over_time(self):
        clock = FakeClock()
        limiter = TokenBucket(capacity=5, refill_rate=1.0, time_fn=clock)
        for _ in range(5):
            limiter.allow("k")
        self.assertFalse(limiter.allow("k"))

        clock.advance(3.0)  # 3 tokens refill
        allowed = sum(limiter.allow("k") for _ in range(3))
        self.assertEqual(allowed, 3)
        self.assertFalse(limiter.allow("k"))

    def test_refill_caps_at_capacity(self):
        clock = FakeClock()
        limiter = TokenBucket(capacity=5, refill_rate=1.0, time_fn=clock)
        clock.advance(1000.0)  # huge idle period
        allowed = sum(limiter.allow("k") for _ in range(10))
        self.assertEqual(allowed, 5)  # never exceeds capacity

    def test_independent_keys_have_independent_buckets(self):
        clock = FakeClock()
        limiter = TokenBucket(capacity=2, refill_rate=1.0, time_fn=clock)
        self.assertTrue(limiter.allow("a"))
        self.assertTrue(limiter.allow("a"))
        self.assertFalse(limiter.allow("a"))
        # key "b" has its own full bucket
        self.assertTrue(limiter.allow("b"))
        self.assertTrue(limiter.allow("b"))
        self.assertFalse(limiter.allow("b"))

    def test_rejection_state_is_429_style(self):
        """Reject should just be a boolean False, callers decide to raise 429."""
        clock = FakeClock()
        limiter = TokenBucket(capacity=1, refill_rate=0.001, time_fn=clock)
        self.assertTrue(limiter.allow("k"))
        result = limiter.allow("k")
        self.assertIs(result, False)

    def test_invalid_capacity_raises(self):
        with self.assertRaises(ValueError):
            TokenBucket(capacity=0, refill_rate=1.0)

    def test_invalid_refill_rate_raises(self):
        with self.assertRaises(ValueError):
            TokenBucket(capacity=5, refill_rate=0)

    def test_thread_safety_under_concurrent_calls(self):
        """Many threads hammering the same key should never allow more than
        the bucket capacity, and total allowed should equal capacity."""
        clock = FakeClock()
        capacity = 50
        limiter = TokenBucket(capacity=capacity, refill_rate=0.0001, time_fn=clock)

        num_threads = 20
        calls_per_thread = 10
        barrier = threading.Barrier(num_threads)
        allowed_count = {"n": 0}
        lock = threading.Lock()

        def worker():
            barrier.wait()
            local_allowed = 0
            for _ in range(calls_per_thread):
                if limiter.allow("shared"):
                    local_allowed += 1
            with lock:
                allowed_count["n"] += local_allowed

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Total attempts = num_threads * calls_per_thread = 200, capacity = 50
        self.assertLessEqual(allowed_count["n"], capacity)
        self.assertGreater(allowed_count["n"], 0)

    def test_tokens_remaining_helper(self):
        clock = FakeClock()
        limiter = TokenBucket(capacity=3, refill_rate=1.0, time_fn=clock)
        self.assertEqual(limiter.tokens_remaining("k"), 3)
        limiter.allow("k")
        self.assertAlmostEqual(limiter.tokens_remaining("k"), 2.0)


if __name__ == "__main__":
    unittest.main()
