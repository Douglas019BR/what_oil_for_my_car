import os
import time
from collections import defaultdict, deque
from threading import Lock

_hits = defaultdict(deque)
_lock = Lock()


def limit_per_minute():
    try:
        return int(os.environ.get("RATE_LIMIT_PER_MINUTE", "120"))
    except ValueError:
        return 120


def allow(ip):
    limit = limit_per_minute()
    if limit <= 0:
        return True
    now = time.monotonic()
    with _lock:
        window = _hits[ip]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            return False
        window.append(now)
        return True


def reset():
    with _lock:
        _hits.clear()
