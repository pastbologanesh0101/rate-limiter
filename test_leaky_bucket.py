import unittest

from ratelimit.leaky_bucket import LeakyBucket
from tests.helpers import FakeClock


class TestLeakyBucket(unittest.TestCase):
    def test_fills_up_to_capacity(self):
        clock = FakeClock()
        bucket = LeakyBucket(capacity=3, leak_rate=1, clock=clock)
        self.assertTrue(bucket.allow())
        self.assertTrue(bucket.allow())
        self.assertTrue(bucket.allow())
        self.assertFalse(bucket.allow())

    def test_drains_at_leak_rate(self):
        clock = FakeClock()
        bucket = LeakyBucket(capacity=2, leak_rate=1, clock=clock)
        self.assertTrue(bucket.allow())
        self.assertTrue(bucket.allow())
        self.assertFalse(bucket.allow())

        clock.advance(1.0)
        self.assertTrue(bucket.allow())

    def test_partial_drain(self):
        clock = FakeClock()
        bucket = LeakyBucket(capacity=1, leak_rate=0.5, clock=clock)
        self.assertTrue(bucket.allow())
        self.assertFalse(bucket.allow())

        clock.advance(1.0)  # level drains from 1.0 to 0.5, still no room for +1
        self.assertFalse(bucket.allow())

        clock.advance(1.0)  # level drains to 0.0, now there's room
        self.assertTrue(bucket.allow())
        self.assertFalse(bucket.allow())


if __name__ == "__main__":
    unittest.main()
