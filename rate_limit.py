"""
The per-caller rate limiter. ← UNIT 9 (capstone)

serve.py asks this, before running the agent: "may this caller make another
request right now?" It answers yes or no, and if no, which limit they hit and
how many seconds until they can try again.

    from rate_limit import check

    allowed, limit, retry_after = check("luis")
    if not allowed:
        ... return a 429 ...

How it counts: a SLIDING window. For each caller it keeps the times of their
recent allowed requests. "5 per minute" means at most 5 in the last 60
seconds, counted back from right now, not "5 between 3:00:00 and 3:00:59".
A fixed clock-minute would let someone send 5 at 3:00:59 and 5 more at
3:01:00: ten in two seconds.

Only ALLOWED requests are counted. A caller who keeps hammering after being
refused doesn't push their own wait further back; they get back in exactly
when their oldest counted request ages out of the window.

The counts live in memory. Restarting the server forgets them, which is fine
for one server on one machine (Path B), and it's also how you reset between
trials.
"""

import threading
import time
from collections import defaultdict, deque

import config

MINUTE = 60
DAY = 24 * 60 * 60

# caller -> times of their allowed requests in the last 24 hours, oldest first
_history: dict[str, deque] = defaultdict(deque)

# Two requests checking the same caller at once must not both see "4 used"
# and both get in as the 5th.
_lock = threading.Lock()


def check(caller: str, now: float | None = None) -> tuple[bool, str | None, int | None]:
    """
    May `caller` make a request now? If yes, the request is counted.

    Returns (allowed, limit, retry_after):
        allowed      True or False
        limit        None if allowed, else which limit was hit, e.g. "5 per minute"
        retry_after  None if allowed, else whole seconds until they can retry

    `now` is only for tests, so they can pretend time has passed without
    waiting. Leave it out and the real clock is used.
    """
    if now is None:
        now = time.monotonic()

    with _lock:
        times = _history[caller]

        # Forget anything older than a day; nothing can use it any more.
        while times and times[0] <= now - DAY:
            times.popleft()

        in_last_minute = sum(1 for t in times if t > now - MINUTE)

        if in_last_minute >= config.HTTP_LIMIT_PER_MINUTE:
            # The oldest request inside the minute is the one that has to age
            # out before there's room again.
            oldest_in_minute = times[-config.HTTP_LIMIT_PER_MINUTE]
            wait = oldest_in_minute + MINUTE - now
            return False, f"{config.HTTP_LIMIT_PER_MINUTE} per minute", max(1, round(wait))

        if len(times) >= config.HTTP_LIMIT_PER_DAY:
            oldest_in_day = times[-config.HTTP_LIMIT_PER_DAY]
            wait = oldest_in_day + DAY - now
            return False, f"{config.HTTP_LIMIT_PER_DAY} per day", max(1, round(wait))

        times.append(now)
        return True, None, None


def reset() -> None:
    """Forget every caller's history. For tests and between trials."""
    with _lock:
        _history.clear()
