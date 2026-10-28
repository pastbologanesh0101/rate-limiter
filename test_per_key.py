import unittest

from ratelimit.per_key import PerKeyLimiter
from ratelimit.token_bucket import TokenBucket
from tests.helpers import FakeClock


class TestPerKeyLimiter(unittest.TestCase):
    def test_keys_are_independent(self):
        clock = FakeClock()
        per_key = PerKeyLimiter(lambda: TokenBucket(capacity=1, refill_rate=1, clock=clock))

        self.assertTrue(per_key.allow("alice"))
        self.assertFalse(per_key.allow("alice"))
        self.assertTrue(per_key.allow("bob"))
        self.assertEqual(len(per_key), 2)

    def test_reuses_limiter_for_same_key(self):
        clock = FakeClock()
        created = []

        def factory():
            limiter = TokenBucket(capacity=2, refill_rate=1, clock=clock)
            created.append(limiter)
            return limiter

        per_key = PerKeyLimiter(factory)
        per_key.allow("alice")
        per_key.allow("alice")
        per_key.allow("alice")
        self.assertEqual(len(created), 1)


if __name__ == "__main__":
    unittest.main()
