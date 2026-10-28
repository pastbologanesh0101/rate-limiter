"""Compares raw throughput (calls/sec to allow()) of each algorithm under
concurrent load. This measures locking/bookkeeping overhead, not real
request handling -- every call uses the real wall clock and a shared
limiter hit from multiple threads.

Usage:
    python3 -m bench.benchmark --threads 8 --duration 2
"""
import argparse
import threading
import time

from ratelimit import (
    FixedWindow,
    LeakyBucket,
    SlidingWindowCounter,
    SlidingWindowLog,
    TokenBucket,
)

LIMIT = 1_000_000  # effectively unbounded, so we measure pure overhead
WINDOW = 1.0

BUILDERS = {
    "token-bucket": lambda: TokenBucket(capacity=LIMIT, refill_rate=LIMIT),
    "leaky-bucket": lambda: LeakyBucket(capacity=LIMIT, leak_rate=LIMIT),
    "fixed-window": lambda: FixedWindow(limit=LIMIT, window_seconds=WINDOW),
    "sliding-log": lambda: SlidingWindowLog(limit=LIMIT, window_seconds=WINDOW),
    "sliding-counter": lambda: SlidingWindowCounter(limit=LIMIT, window_seconds=WINDOW),
}


def run_one(name, builder, num_threads, duration):
    limiter = builder()
    counts = [0] * num_threads
    stop_at = time.monotonic() + duration

    def worker(idx):
        local_count = 0
        while time.monotonic() < stop_at:
            limiter.allow()
            local_count += 1
        counts[idx] = local_count

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - start

    total = sum(counts)
    print(f"{name:>18}: {total:>10,} calls in {elapsed:5.2f}s -> {total / elapsed:>12,.0f} ops/sec")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--duration", type=float, default=2.0)
    args = parser.parse_args()

    print(f"threads={args.threads} duration={args.duration}s\n")
    for name, builder in BUILDERS.items():
        run_one(name, builder, args.threads, args.duration)


if __name__ == "__main__":
    main()
