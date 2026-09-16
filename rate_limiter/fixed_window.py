"""Fixed Window Counter rate limiter.

Time is divided into fixed-size windows of ``window_seconds``. Each key gets
a counter that increments on every allowed request within the current
window and resets to zero when a new window begins.
"""

import threading
import time
from typing import Callable, Dict, Tuple


class FixedWindowCounter:
    """Fixed window counter rate limiter.

    Tradeoffs:
      * Very cheap: O(1) memory per key (just a counter + window id).
      * Simple to reason about and implement.
      * Can allow up to 2x the limit at window boundaries (a burst right
        before a window ends, followed by another burst right after it
        starts), unlike sliding window approaches.
    """

    def __init__(
        self,
        limit: int,
        window_seconds: float,
        time_fn: Callable[[], float] = time.monotonic,
    ):
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.limit = limit
        self.window_seconds = float(window_seconds)
        self._time_fn = time_fn
        self._lock = threading.Lock()
        # key -> (window_index, count)
        self._counters: Dict[str, Tuple[int, int]] = {}

    def _window_index(self, now: float) -> int:
        return int(now // self.window_seconds)

    def allow(self, key: str) -> bool:
        now = self._time_fn()
        current_window = self._window_index(now)
        with self._lock:
            window_index, count = self._counters.get(key, (current_window, 0))
            if window_index != current_window:
                # New window: reset the counter.
                window_index, count = current_window, 0

            if count < self.limit:
                self._counters[key] = (window_index, count + 1)
                return True

            self._counters[key] = (window_index, count)
            return False

    def current_count(self, key: str) -> int:
        """Introspection helper, mainly useful for tests/demo."""
        now = self._time_fn()
        current_window = self._window_index(now)
        with self._lock:
            window_index, count = self._counters.get(key, (current_window, 0))
            return count if window_index == current_window else 0
