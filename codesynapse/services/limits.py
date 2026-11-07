"""Limits how often each user can start expensive work, so one person can't use up the AI quota.

Counts are kept in memory, which suits the single-process deployment. Running several
processes would need a shared store such as Redis.
"""
import threading
import time
from collections import defaultdict, deque

# Action: (allowed requests, per this many seconds)
LIMITS = {
    "signup": (30, 3600),
    "index": (10, 3600),
    "job": (20, 3600),
    "analysis": (5, 3600),
    "chat": (40, 3600),
}

class Limited(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after
        minutes = max(1, round(retry_after / 60))
        super().__init__(f"You've reached the limit for this. Please try again in about {minutes} minute{'s' * (minutes != 1)}.")

_hits = defaultdict(deque)
_lock = threading.Lock()

def check(action, key):
    """Records one use of `action` by `key`, or raises Limited if the limit is reached."""
    allowed, window = LIMITS[action]
    now = time.monotonic()
    with _lock:
        hits = _hits[(action, key)]
        while hits and now - hits[0] >= window:
            hits.popleft()
        if len(hits) >= allowed:
            # A limit of 0 switches the action off, so there is no earlier request to wait for
            raise Limited(int(window - (now - hits[0])) + 1 if hits else window)
        hits.append(now)

def reset():
    with _lock:
        _hits.clear()
