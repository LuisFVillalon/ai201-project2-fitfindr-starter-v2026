"""
The request log. ← UNIT 9 (capstone)

Every request that reaches `serve.py`'s `/ask` route gets written here as one
JSON object per line (JSONL), in logs/requests.jsonl. Not `print()`: a file
you can read back after the server has stopped.

Every entry has the SAME fields, even when some of them are None. A request
that was rate-limited never ran the agent, so it has no selected item, but it
still has a `selected_item_id` key set to None. That way every line can be
compared with every other line, and a missing value means "didn't happen",
never "forgot to log it".

    from request_log import log_request, read_entries

    log_request(event="ask", user_id="luis", query="...", http_status=200, ...)
    entries = read_entries(limit=20)
"""

import json
import threading
from datetime import datetime, timezone

import config

LOG_PATH = config.ROOT / "logs" / "requests.jsonl"

# Only one thread may write at a time, so two log lines can never interleave
# into one broken line. (serve.py runs one agent at a time already, but a
# rejected request can be logged while another request's agent is running.)
_lock = threading.Lock()

# The fixed shape of every entry, in the order they are written.
FIELDS = (
    "timestamp",         # when the request arrived, UTC, ISO 8601
    "event",             # "ask" (agent ran), "rejected" (400/429), or "error" (500)
    "user_id",           # who asked: the body's user_id, or "ip:<address>"
    "query",             # what they asked, exactly as sent
    "http_status",       # what we answered: 200, 400, 429, 500
    "duration_ms",       # how long the whole request took, start to response
    "parsed",            # the agent's {description, size, max_price}
    "result_count",      # how many listings search_listings returned
    "selected_item_id",  # which listing the agent picked, e.g. "lst_002"
    "stopped_early",     # True if search found nothing and the agent stopped
    "error",             # the agent's session["error"], or why we rejected/failed
    "prompt_tokens",     # tokens sent to the model for THIS request
    "output_tokens",     # tokens the model sent back for THIS request
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def log_request(**fields) -> dict:
    """
    Write one request to the log and return the entry that was written.

    Any of FIELDS you don't pass is written as None. Anything you pass that is
    NOT in FIELDS is still written, after the fixed fields (e.g. `limit` on a
    rate-limited rejection), so nothing you meant to record is dropped.
    """
    entry = {name: None for name in FIELDS}
    entry["timestamp"] = _now()
    entry.update(fields)

    line = json.dumps(entry, ensure_ascii=False, default=str)
    with _lock:
        LOG_PATH.parent.mkdir(exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return entry


def read_entries(limit: int | None = None) -> list[dict]:
    """The logged entries, oldest first. `limit` keeps only the newest N."""
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open(encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]
    return entries[-limit:] if limit else entries
