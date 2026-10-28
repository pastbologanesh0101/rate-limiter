import unittest

from ratelimit.sliding_window_log import SlidingWindowLog
from tests.helpers import FakeClock


class TestSlidingWindowLog(unittest.TestCase):
    def test_allows_up_to_limit(self):
        clock = FakeClock()
        log = SlidingWindowLog(limit=3, window_seconds=10, clock=clock)
        self.assertTrue(log.allow())
        self.assertTrue(log.allow())
        self.assertTrue(log.allow())
        self.assertFalse(log.allow())

    def test_old_entries_expire_individually(self):
        clock = FakeClock()
        log = SlidingWindowLog(limit=2, window_seconds=10, clock=clock)
        self.assertTrue(log.allow())  # t=0

        clock.advance(5.0)
        self.assertTrue(log.allow())  # t=5
        self.assertFalse(log.allow())  # still full

        clock.advance(5.1)  # t=10.1, the t=0 entry expires, t=5 one doesn't
        self.assertTrue(log.allow())
        self.assertFalse(log.allow())

    def test_no_boundary_burst(self):
        # Unlike fixed window, sliding log never exceeds the limit in any
        # window_seconds-wide trailing interval.
        clock = FakeClock()
        log = SlidingWindowLog(limit=5, window_seconds=10, clock=clock)
        for _ in range(5):
            self.assertTrue(log.allow())

        clock.advance(9.9)
        self.assertFalse(log.allow())

        clock.advance(0.2)
        self.assertTrue(log.allow())


if __name__ == "__main__":
    unittest.main()
