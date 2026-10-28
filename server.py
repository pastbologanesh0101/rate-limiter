"""Small HTTP server that rate-limits requests per client IP.

Usage:
    python3 -m demo.server --algo token-bucket --limit 5 --window 10
    curl http://localhost:8000/

Run several curls in a row to see 429s once the limit is hit.
"""
import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ratelimit import (
    FixedWindow,
    LeakyBucket,
    PerKeyLimiter,
    SlidingWindowCounter,
    SlidingWindowLog,
    TokenBucket,
)

ALGORITHMS = {
    "token-bucket": lambda limit, window: TokenBucket(capacity=limit, refill_rate=limit / window),
    "leaky-bucket": lambda limit, window: LeakyBucket(capacity=limit, leak_rate=limit / window),
    "fixed-window": lambda limit, window: FixedWindow(limit=limit, window_seconds=window),
    "sliding-log": lambda limit, window: SlidingWindowLog(limit=limit, window_seconds=window),
    "sliding-counter": lambda limit, window: SlidingWindowCounter(limit=limit, window_seconds=window),
}


def make_handler(per_key: PerKeyLimiter):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            key = self.client_address[0]
            if per_key.allow(key):
                body = b"ok\n"
                self.send_response(200)
            else:
                body = b"rate limit exceeded\n"
                self.send_response(429)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            sys.stderr.write(f"{self.client_address[0]} {fmt % args}\n")

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algo", choices=ALGORITHMS.keys(), default="token-bucket")
    parser.add_argument("--limit", type=int, default=5, help="requests allowed per window")
    parser.add_argument("--window", type=float, default=10.0, help="window size in seconds")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    factory = lambda: ALGORITHMS[args.algo](args.limit, args.window)  # noqa: E731
    per_key = PerKeyLimiter(factory)

    server = ThreadingHTTPServer(("localhost", args.port), make_handler(per_key))
    print(
        f"serving on http://localhost:{args.port} "
        f"[{args.algo}, limit={args.limit}/{args.window}s per client IP]"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
