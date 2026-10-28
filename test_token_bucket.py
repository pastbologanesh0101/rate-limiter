import unittest

from ratelimit.token_bucket import TokenBucket
from tests.helpers import FakeClock


class TestTokenBucket(unittest.TestCase):
    def test_allows_burst_up_to_capacity(self):
        clock = FakeClock()
        bucket = TokenBucket(capacity=5, refill_rate=1, clock=clock)
        for _ in range(5):
            self.assertTrue(bucket.allow())
        self.assertFalse(bucket.allow())

    def test_refills_over_time(self):
        clock = FakeClock()
        bucket = TokenBucket(capacity=2, refill_rate=1, clock=clock)
        self.assertTrue(bucket.allow())
        self.assertTrue(bucket.allow())
        self.assertFalse(bucket.allow())

        clock.advance(1.0)
        self.assertTrue(bucket.allow())
        self.assertFalse(bucket.allow())

    def test_never_exceeds_capacity(self):
        clock = FakeClock()
        bucket = TokenBucket(capacity=3, refill_rate=10, clock=clock)
        clock.advance(100)
        self.assertTrue(bucket.allow(3))
        self.assertFalse(bucket.allow())

    def test_allow_n(self):
        clock = FakeClock()
        bucket = TokenBucket(capacity=10, refill_rate=1, clock=clock)
        self.assertTrue(bucket.allow(7))
        self.assertFalse(bucket.allow(4))
        self.assertTrue(bucket.allow(3))

    def test_rejects_invalid_params(self):
        with self.assertRaises(ValueError):
            TokenBucket(capacity=0, refill_rate=1)
        with self.assertRaises(ValueError):
            TokenBucket(capacity=1, refill_rate=0)


if __name__ == "__main__":
    unittest.main()
