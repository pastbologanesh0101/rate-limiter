import unittest

from ratelimit.sliding_window_counter import SlidingWindowCounter
from tests.helpers import FakeClock


class TestSlidingWindowCounter(unittest.TestCase):
    def test_allows_up_to_limit_in_first_window(self):
        clock = FakeClock()
        counter = SlidingWindowCounter(limit=4, window_seconds=10, clock=clock)
        for _ in range(4):
            self.assertTrue(counter.allow())
        self.assertFalse(counter.allow())

    def test_blends_previous_window_near_boundary(self):
        clock = FakeClock()
        counter = SlidingWindowCounter(limit=10, window_seconds=10, clock=clock)
        for _ in range(10):
            self.assertTrue(counter.allow())  # fills window [0, 10)

        clock.advance(10.0)  # now at the very start of the next window
        # previous window is fully weighted (elapsed=0 -> weight=1), so the
        # blended estimate is still ~10 and the request should be rejected.
        self.assertFalse(counter.allow())

    def test_weight_decays_through_the_window(self):
        clock = FakeClock()
        counter = SlidingWindowCounter(limit=10, window_seconds=10, clock=clock)
        for _ in range(10):
            counter.allow()

        clock.advance(15.0)  # halfway through the next window
        # weight on previous window's 10 requests is now 0.5 -> estimate ~5,
        # leaving roughly half the limit available.
        allowed = sum(1 for _ in range(5) if counter.allow())
        self.assertGreaterEqual(allowed, 4)
        self.assertLessEqual(allowed, 5)

    def test_old_windows_fully_expire(self):
        clock = FakeClock()
        counter = SlidingWindowCounter(limit=5, window_seconds=10, clock=clock)
        for _ in range(5):
            counter.allow()

        clock.advance(25.0)  # two full windows later, previous window is stale
        self.assertTrue(counter.allow())


if __name__ == "__main__":
    unittest.main()
