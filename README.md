# Rate Limiter

A small, pure-Python library implementing three classic rate-limiting
algorithms behind a common interface. No external services, no dependencies
beyond the standard library — this is a backend/systems project focused on
correctness, concurrency safety, and testability rather than a web
framework.

## Algorithms

All limiters implement:

```python
limiter.allow(key: str) -> bool
```

`allow` returns `True` if a request for `key` should proceed, and `False` if
it should be rejected (the equivalent of an HTTP `429 Too Many Requests`
response). Each limiter is thread-safe (guarded by an internal `threading.Lock`)
and clock-injectable: every constructor accepts a `time_fn` callable
(defaulting to `time.monotonic`), so tests and callers can control time
deterministically without real `sleep()` calls.

### Token Bucket (`rate_limiter.TokenBucket`)

Each key gets a bucket holding up to `capacity` tokens, refilled continuously
at `refill_rate` tokens/second. Every allowed request consumes one token.

- **Pros:** allows short bursts up to `capacity`, then smoothly throttles to
  the steady-state `refill_rate`. No hard window edges, so there's no
  "double burst" problem.
- **Cons:** slightly more state per key (float tokens + last refill time) and
  a bit more conceptually involved than a plain counter.
- **Good for:** APIs that want to permit occasional bursts while enforcing a
  long-run average (e.g. "100 requests/minute, but you can burst to 20 at
  once").

### Fixed Window Counter (`rate_limiter.FixedWindowCounter`)

Time is divided into fixed-size windows of `window_seconds`. Each key has a
counter that increments per allowed request and resets to zero when the
window rolls over.

- **Pros:** extremely cheap — O(1) memory per key, trivial to implement and
  reason about.
- **Cons:** can allow up to 2x the limit across a window boundary (a burst
  right before the window ends, followed immediately by another burst right
  after the next window starts).
- **Good for:** simple, coarse-grained limits where boundary bursts are an
  acceptable tradeoff for simplicity (e.g. "1000 requests/hour").

### Sliding Window Log (`rate_limiter.SlidingWindowLog`)

Each key keeps a log of timestamps of its recent allowed requests. On every
call, timestamps older than `window_seconds` are evicted, then the request
is allowed only if the remaining log is shorter than `limit`.

- **Pros:** exact — at any instant, at most `limit` requests are permitted in
  the trailing `window_seconds`. No boundary-burst problem.
- **Cons:** O(limit) memory per key (must store timestamps) and slightly more
  CPU work per call.
- **Good for:** limits where precision matters more than memory footprint
  (e.g. login attempt throttling, abuse prevention).

### `@rate_limited` decorator

`rate_limiter.rate_limited(limiter, key_fn=None)` wraps any function so
calls are gated by `limiter.allow(key)`. If the call is rejected, it raises
`RateLimitExceeded` (a stand-in for an HTTP 429 response). `key_fn` derives
the rate-limit key from the call arguments, letting one limiter track
independent limits per user/IP/etc.

```python
from rate_limiter import FixedWindowCounter, rate_limited, RateLimitExceeded

limiter = FixedWindowCounter(limit=3, window_seconds=60)

@rate_limited(limiter, key_fn=lambda user: user)
def handle_request(user: str) -> str:
    return f"handled request for {user}"

try:
    handle_request("alice")
except RateLimitExceeded:
    ...  # respond with HTTP 429
```

## Usage

```python
from rate_limiter import TokenBucket, FixedWindowCounter, SlidingWindowLog

bucket = TokenBucket(capacity=5, refill_rate=1.0)   # 5 burst, 1 req/s steady
window = FixedWindowCounter(limit=100, window_seconds=60)   # 100 req/min
log = SlidingWindowLog(limit=10, window_seconds=1)   # 10 req/sec, exact

if bucket.allow("user-123"):
    ...  # handle request
else:
    ...  # return 429
```

Pass a custom `time_fn` to any limiter to control its clock (useful for
tests, simulations, or decoupling from wall-clock time):

```python
fake_now = [0.0]
limiter = TokenBucket(capacity=5, refill_rate=1.0, time_fn=lambda: fake_now[0])
fake_now[0] += 3.0  # simulate 3 seconds passing, no real sleep needed
```

## Demo

`demo.py` simulates bursts of requests against each limiter (using a fake,
manually-advanced clock — no real sleeping) and prints allowed/rejected
counts, plus a demonstration of the `@rate_limited` decorator.

```
$ python demo.py

=== Token Bucket (capacity=5, refill_rate=1/s) ===
Initial burst of 10 requests -> allowed=5, rejected=5
Advancing fake clock by 3 seconds (refills 3 tokens)...
Next burst of 10 requests   -> allowed=3, rejected=7

=== Fixed Window Counter (limit=5, window=10s) ===
Burst of 10 requests in window 1 -> allowed=5, rejected=5
Advancing fake clock by 10 seconds (new window)...
Burst of 10 requests in window 2 -> allowed=5, rejected=5

=== Sliding Window Log (limit=5, window=10s) ===
Burst of 10 requests -> allowed=5, rejected=5
Advancing fake clock by 6 seconds (partial slide)...
5 more requests      -> allowed=0, rejected=5
Advancing fake clock by 5 more seconds (old entries expire)...
5 more requests      -> allowed=5, rejected=0

=== @rate_limited decorator on a plain function ===
  call 1: handled request for alice
  call 2: handled request for alice
  call 3: handled request for alice
  call 4: REJECTED (429) - Rate limit exceeded for key='alice'
  call 5: REJECTED (429) - Rate limit exceeded for key='alice'
```

## Testing

Tests use only the standard library (`unittest`) and are also compatible
with `pytest`. Each algorithm has its own test module covering: allowing up
to the limit, rejecting over the limit, resetting/sliding after the window
elapses (via the injectable clock — no real sleeping), thread safety under
many concurrent threads calling `.allow()` on the same key, and 429-style
rejection state.

```bash
python -m unittest discover -s tests -v
# or
pytest tests/ -v
```

33 tests, all passing, run in milliseconds since no real time.sleep() is used
anywhere in the suite.

## Project layout

```
rate_limiter/
  base.py               # BaseRateLimiter interface
  token_bucket.py        # TokenBucket
  fixed_window.py         # FixedWindowCounter
  sliding_window_log.py    # SlidingWindowLog
  decorator.py            # @rate_limited + RateLimitExceeded
demo.py                  # runnable demo, no dependencies
tests/                   # unittest test suite, one module per algorithm
.github/workflows/tests.yml  # CI: runs tests on Python 3.11 and 3.12
```

## License

MIT, see [LICENSE](LICENSE).
