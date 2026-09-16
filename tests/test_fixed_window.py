import threading
import unittest

from rate_limiter import FixedWindowCounter


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestFixedWindowCounter(unittest.TestCase):
    def test_allows_up_to_limit(self):
        clock = FakeClock()
        limiter = FixedWindowCounter(limit=5, window_seconds=10.0, time_fn=clock)
        results = [limiter.allow("k") for _ in range(5)]
        self.assertTrue(all(results))

    def test_rejects_over_limit(self):
        clock = FakeClock()
        limiter = FixedWindowCounter(limit=5, window_seconds=10.0, time_fn=clock)
        for _ in range(5):
            limiter.allow("k")
        self.assertFalse(limiter.allow("k"))
        self.assertFalse(limiter.allow("k"))

    def test_resets_after_window_elapses(self):
        clock = FakeClock()
        limiter = FixedWindowCounter(limit=5, window_seconds=10.0, time_fn=clock)
        for _ in range(5):
            self.assertTrue(limiter.allow("k"))
        self.assertFalse(limiter.allow("k"))

        clock.advance(10.0)  # move into next window
        self.assertTrue(limiter.allow("k"))

    def test_does_not_reset_before_window_elapses(self):
        clock = FakeClock()
        limiter = FixedWindowCounter(limit=2, window_seconds=10.0, time_fn=clock)
        limiter.allow("k")
        limiter.allow("k")
        clock.advance(9.9)
        self.assertFalse(limiter.allow("k"))

    def test_independent_keys(self):
        clock = FakeClock()
        limiter = FixedWindowCounter(limit=1, window_seconds=10.0, time_fn=clock)
        self.assertTrue(limiter.allow("a"))
        self.assertFalse(limiter.allow("a"))
        self.assertTrue(limiter.allow("b"))

    def test_rejection_state_is_429_style(self):
        clock = FakeClock()
        limiter = FixedWindowCounter(limit=1, window_seconds=10.0, time_fn=clock)
        self.assertTrue(limiter.allow("k"))
        self.assertIs(limiter.allow("k"), False)

    def test_invalid_limit_raises(self):
        with self.assertRaises(ValueError):
            FixedWindowCounter(limit=0, window_seconds=10.0)

    def test_invalid_window_raises(self):
        with self.assertRaises(ValueError):
            FixedWindowCounter(limit=5, window_seconds=0)

    def test_current_count_helper(self):
        clock = FakeClock()
        limiter = FixedWindowCounter(limit=5, window_seconds=10.0, time_fn=clock)
        self.assertEqual(limiter.current_count("k"), 0)
        limiter.allow("k")
        limiter.allow("k")
        self.assertEqual(limiter.current_count("k"), 2)
        clock.advance(10.0)
        self.assertEqual(limiter.current_count("k"), 0)

    def test_thread_safety_under_concurrent_calls(self):
        """Many threads hitting the same key concurrently should never allow
        more than `limit` requests through in the same window."""
        clock = FakeClock()
        limit = 30
        limiter = FixedWindowCounter(limit=limit, window_seconds=100.0, time_fn=clock)

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

        self.assertEqual(allowed_count["n"], limit)


if __name__ == "__main__":
    unittest.main()
