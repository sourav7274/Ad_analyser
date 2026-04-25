"""
Simple in-memory metrics tracker.

Tracks request counts per endpoint and outcome. Not persistent across
restarts — for production use, replace with Prometheus or CloudWatch.
"""

import threading
from collections import defaultdict


class MetricsTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._counters: dict[str, int] = defaultdict(int)

    def increment(self, key: str) -> None:
        with self._lock:
            self._counters[key] += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)


# Module-level singleton
metrics = MetricsTracker()
