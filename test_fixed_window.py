import unittest

from ratelimit.fixed_window import FixedWindow
from tests.helpers import FakeClock


class TestFixedWindow(unittest.TestCase):
    def test_allows_up_to_limit_per_window(self):
        clock = FakeClock()
        window = FixedWindow(limit=3, window_seconds=10, clock=clock)
        self.assertTrue(window.allow())
        self.assertTrue(window.allow())
        self.assertTrue(window.allow())
        self.assertFalse(window.allow())

    def test_resets_on_new_window(self):
        clock = FakeClock()
        window = FixedWindow(limit=2, window_seconds=10, clock=clock)
        self.assertTrue(window.allow())
        self.assertTrue(window.allow())
        self.assertFalse(window.allow())

        clock.advance(10.0)
        self.assertTrue(window.allow())
        self.assertTrue(window.allow())
        self.assertFalse(window.allow())

    def test_boundary_burst_is_a_known_limitation(self):
        # Demonstrates why fixed windows allow up to 2x the limit near an edge.
        clock = FakeClock()
        window = FixedWindow(limit=5, window_seconds=10, clock=clock)
        for _ in range(5):
            self.assertTrue(window.allow())

        clock.advance(10.0)
        for _ in range(5):
            self.assertTrue(window.allow())
        self.assertFalse(window.allow())


if __name__ == "__main__":
    unittest.main()
