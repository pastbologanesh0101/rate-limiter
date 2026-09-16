import threading
import unittest

from rate_limiter import SlidingWindowLog


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestSlidingWindowLog(unittest.TestCase):
    def test_allows_up_to_limit(self):
        clock = FakeClock()
        limiter = SlidingWindowLog(limit=5, window_seconds=10.0, time_fn=clock)
        results = [limiter.allow("k") for _ in range(5)]
        self.assertTrue(all(results))

    def test_rejects_over_limit(self):
        clock = FakeClock()
        limiter = SlidingWindowLog(limit=5, window_seconds=10.0, time_fn=clock)
        for _ in range(5):
            limiter.allow("k")
        self.assertFalse(limiter.allow("k"))
        self.assertFalse(limiter.allow("k"))

    def test_resets_after_window_elapses(self):
        clock = FakeClock()
        limiter = SlidingWindowLog(limit=5, window_seconds=10.0, time_fn=clock)
        for _ in range(5):
            self.assertTrue(limiter.allow("k"))
        self.assertFalse(limiter.allow("k"))

        clock.advance(10.1)  # all old entries expire
        self.assertTrue(limiter.allow("k"))

    def test_sliding_behavior_partial_expiry(self):
        """Only entries older than the window should expire; the window
        truly slides rather than resetting all-or-nothing."""
        clock = FakeClock()
        limiter = SlidingWindowLog(limit=3, window_seconds=10.0, time_fn=clock)
        limiter.allow("k")  # t=0
        clock.advance(5.0)
        limiter.allow("k")  # t=5
        limiter.allow("k")  # t=5, log full (3 entries: 0, 5, 5)
        self.assertFalse(limiter.allow("k"))  # still full

        clock.advance(5.1)  # t=10.1, the t=0 entry expires (0 <= 10.1-10)
        self.assertTrue(limiter.allow("k"))  # one slot freed

    def test_independent_keys(self):
        clock = FakeClock()
        limiter = SlidingWindowLog(limit=1, window_seconds=10.0, time_fn=clock)
        self.assertTrue(limiter.allow("a"))
        self.assertFalse(limiter.allow("a"))
        self.assertTrue(limiter.allow("b"))

    def test_rejection_state_is_429_style(self):
        clock = FakeClock()
        limiter = SlidingWindowLog(limit=1, window_seconds=10.0, time_fn=clock)
        self.assertTrue(limiter.allow("k"))
        self.assertIs(limiter.allow("k"), False)

    def test_invalid_limit_raises(self):
        with self.assertRaises(ValueError):
            SlidingWindowLog(limit=0, window_seconds=10.0)

    def test_invalid_window_raises(self):
        with self.assertRaises(ValueError):
            SlidingWindowLog(limit=5, window_seconds=0)

    def test_current_count_helper(self):
        clock = FakeClock()
        limiter = SlidingWindowLog(limit=5, window_seconds=10.0, time_fn=clock)
        self.assertEqual(limiter.current_count("k"), 0)
        limiter.allow("k")
        limiter.allow("k")
        self.assertEqual(limiter.current_count("k"), 2)
        clock.advance(10.1)
        self.assertEqual(limiter.current_count("k"), 0)

    def test_thread_safety_under_concurrent_calls(self):
        """Many threads hitting the same key concurrently should never allow
        more than `limit` requests through within the window."""
        clock = FakeClock()
        limit = 30
        limiter = SlidingWindowLog(limit=limit, window_seconds=100.0, time_fn=clock)

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
