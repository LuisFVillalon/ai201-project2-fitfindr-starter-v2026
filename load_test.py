#!/usr/bin/env python3
"""
The capstone stretch: a load observation. ← UNIT 9

    (terminal 1)  $env:AI201_CACHE = '0'; python serve.py
    (terminal 2)  python load_test.py

"Normal rate" here is 5 requests a minute: the most one caller is allowed
(config.HTTP_LIMIT_PER_MINUTE), and about the pace measure_cost.py ran at.
Ten times that is 50 requests in one minute, one every 1.2 s, sent two ways:

  A. one caller sending all 50          → tests my per-caller rate limit
  B. ten callers sending 5 each, mixed  → every request passes the limit, so
                                          this tests serve.py's one-at-a-time
                                          lock and generate.py's 15-calls-a-
                                          minute pacing behind it

Requests are fired on schedule from their own threads, without waiting for
earlier ones to answer, the way real users would. Everything is scored from
logs/requests.jsonl, and the report is written to results/.
"""

import json
import statistics
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime

import config
from request_log import read_entries

BASE = "http://localhost:5000"
PER_MINUTE = 50            # 10 × the normal 5 per minute
INTERVAL_S = 60 / PER_MINUTE
CALLERS_B = 10
CLIENT_TIMEOUT_S = 900     # B queues behind the lock; don't give up early
PRICE_IN, PRICE_OUT = 0.30, 2.50

# The same 10 matching queries measure_cost.py used, so every allowed request
# is a complete run (two model calls), the expensive case.
QUERIES = [
    "vintage graphic tee under $30", "denim jacket size M", "black combat boots",
    "oversized crewneck sweatshirt under $25", "leather belt", "band tee size L",
    "flannel shirt under $40", "bucket hat", "mesh long-sleeve top size S",
    "vintage polo shirt",
]


def post(body: dict) -> int:
    req = urllib.request.Request(f"{BASE}/ask", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=CLIENT_TIMEOUT_S) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception as exc:                       # timeout, connection refused
        return f"client:{type(exc).__name__}"


def fire(plan: list[tuple[str, str]]) -> list:
    """Send each (user_id, query) INTERVAL_S apart, each on its own thread."""
    statuses = [None] * len(plan)

    def one(i, uid, q):
        statuses[i] = post({"query": q, "user_id": uid})

    threads = []
    start = time.monotonic()
    for i, (uid, q) in enumerate(plan):
        time.sleep(max(0, start + i * INTERVAL_S - time.monotonic()))
        t = threading.Thread(target=one, args=(i, uid, q))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    return statuses


def cost(e: dict) -> float:
    return ((e.get("prompt_tokens") or 0) / 1e6 * PRICE_IN
            + (e.get("output_tokens") or 0) / 1e6 * PRICE_OUT)


def summarise(name: str, uids: set[str], statuses: list, wall_s: float) -> tuple[list[str], list[dict]]:
    lines = sorted((e for e in read_entries() if e.get("user_id") in uids),
                   key=lambda e: e["timestamp"])
    by_status: dict = {}
    for e in lines:
        by_status[e["http_status"]] = by_status.get(e["http_status"], 0) + 1
    ok = [e for e in lines if e["http_status"] == 200]
    refused = [e for e in lines if e["http_status"] == 429]
    complete = [e for e in ok if not e["stopped_early"]]
    client_errors = [s for s in statuses if isinstance(s, str)]

    out = [f"### {name}", "",
           "| Measure | Value |", "|---|---|",
           f"| Requests sent | {len(statuses)} in {len(statuses) * INTERVAL_S:.0f} s ({PER_MINUTE}/min) |",
           f"| Log lines written | {len(lines)} |",
           f"| By status | {', '.join(f'{k}: {v}' for k, v in sorted(by_status.items()))} |",
           f"| Client-side failures (timeout / no answer) | {len(client_errors)} |"]
    if refused:
        d = [e["duration_ms"] for e in refused]
        out.append(f"| 429 duration_ms (min / median / max) | {min(d)} / {statistics.median(d):g} / {max(d)} |")
    if ok:
        d = [e["duration_ms"] for e in ok]
        out.append(f"| 200 duration_ms (min / median / max) | {min(d):,} / {statistics.median(d):,.0f} / {max(d):,} |")
        out.append(f"| Complete runs (fit card) / stopped early | {len(complete)} / {len(ok) - len(complete)} |")
        errs = sorted({e['error'] for e in ok if e['error']})
        if errs:
            out.append(f"| Errors on 200s | {'; '.join(errs)} |")
    if complete:
        span = (datetime.fromisoformat(complete[-1]["timestamp"])
                - datetime.fromisoformat(complete[0]["timestamp"])).total_seconds()
        rate = (len(complete) - 1) / span * 60 if span else float("nan")
        total = sum(cost(e) for e in complete)
        out.append(f"| Complete runs finished per minute | {rate:.1f} |")
        out.append(f"| Tokens / cost of complete runs | "
                   f"{sum(e['prompt_tokens'] or 0 for e in complete):,} + "
                   f"{sum(e['output_tokens'] or 0 for e in complete):,} = ${total:.6f} |")
    out.append(f"| Wall time until the last answer | {wall_s:,.0f} s |")
    out.append("")
    return out, lines


def main() -> None:
    try:
        urllib.request.urlopen(f"{BASE}/health", timeout=5)
    except Exception:
        raise SystemExit("serve.py isn't running. Start it first (see the docstring).")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = ["# Capstone stretch — load observation at 10× normal rate", "",
              f"`python load_test.py` on {datetime.now():%Y-%m-%d %H:%M}, against "
              f"`python serve.py` with AI201_CACHE={config.CACHE_ENABLED and '1' or '0'}. "
              f"Normal rate = {config.HTTP_LIMIT_PER_MINUTE} requests/minute (the per-caller limit); "
              f"10× = {PER_MINUTE} requests in one minute, one every {INTERVAL_S:.1f} s, "
              "each on its own thread so none waits for an earlier answer before sending.", ""]
    samples = []

    # A: one caller, all 50.
    uid_a = f"loadA_{stamp}"
    plan_a = [(uid_a, QUERIES[i % len(QUERIES)]) for i in range(PER_MINUTE)]
    print(f"A: one caller, {PER_MINUTE} requests in 60 s ...")
    t0 = time.monotonic()
    st_a = fire(plan_a)
    out, lines_a = summarise("A. One caller at 50 per minute", {uid_a}, st_a, time.monotonic() - t0)
    report += out
    print("\n".join(out))
    samples += [lines_a[0]] + [e for e in lines_a if e["http_status"] == 429][:1]

    # Let A's minute expire so it can't affect B (different user_ids anyway).
    time.sleep(5)

    # B: ten callers, 5 each, round-robin so each caller is at the normal rate.
    uids_b = [f"loadB{n:02d}_{stamp}" for n in range(CALLERS_B)]
    plan_b = [(uids_b[i % CALLERS_B], QUERIES[i % len(QUERIES)]) for i in range(PER_MINUTE)]
    print(f"\nB: {CALLERS_B} callers × {PER_MINUTE // CALLERS_B} requests in 60 s "
          "(this queues; expect several minutes) ...")
    t0 = time.monotonic()
    st_b = fire(plan_b)
    out, lines_b = summarise(f"B. Ten callers at 5 per minute each ({PER_MINUTE}/min total)",
                             set(uids_b), st_b, time.monotonic() - t0)
    report += out
    print("\n".join(out))
    ok_b = [e for e in lines_b if e["http_status"] == 200]
    if ok_b:
        samples += [min(ok_b, key=lambda e: e["duration_ms"]), max(ok_b, key=lambda e: e["duration_ms"])]
    samples += [e for e in lines_b if e["http_status"] not in (200,)][:2]

    report += ["### Sample log lines (`request_log.py::log_request`, from `serve.py::ask`)", "",
               "A's first request, A's first refusal, B's fastest and slowest 200, "
               "and B's first non-200 if there was one.", "", "```json"]
    report += [json.dumps(e, ensure_ascii=False) for e in samples]
    report += ["```", "", "### Every log line from this run", "", "```json"]
    report += [json.dumps(e, ensure_ascii=False) for e in lines_a + lines_b]
    report += ["```", ""]

    path = config.ROOT / "results" / f"capstone_load_{stamp}.md"
    path.write_text("\n".join(report), encoding="utf-8")
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
