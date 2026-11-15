#!/usr/bin/env python3
"""
Measure what one FitFindr run costs. ← UNIT 9 (capstone)

    (terminal 1)  $env:AI201_CACHE = '0'; python serve.py
    (terminal 2)  python measure_cost.py

Sends 10 different matching queries to the RUNNING server, the same way a
user would, then reads back the log lines those requests wrote and turns
their token counts into dollars. Nothing here estimates tokens: every number
comes from logs/requests.jsonl, which got them from the API's own
usage_metadata (generate.py::_record_tokens).

The server must be started with the cache OFF. A cached answer makes no model
call and logs 0 tokens, which would make a run look free.

Requests are spaced PACE_S seconds apart, because the server's own rate limit
(5 per minute per caller) would otherwise turn the 6th one into a 429.
"""

import json
import sys
import time
import urllib.error
import urllib.request

import config  # noqa: F401  (UTF-8 console on Windows)
from request_log import read_entries

URL = "http://localhost:5000/ask"
PACE_S = 13  # 60 s / 5 per minute = 12 s; one extra second of margin

# Ten queries that each match, and each select a DIFFERENT listing, so the
# average is over the catalog, not one item. Checked with search_listings
# (no model) before measuring.
QUERIES = [
    "vintage graphic tee under $30",
    "denim jacket size M",
    "black combat boots",
    "oversized crewneck sweatshirt under $25",
    "leather belt",
    "band tee size L",
    "flannel shirt under $40",
    "bucket hat",
    "mesh long-sleeve top size S",
    "vintage polo shirt",
]

# gemini-3.5-flash-lite, standard paid tier, from
# https://ai.google.dev/gemini-api/docs/pricing (checked 2026-11-14).
# Output tokens include thinking tokens; this model reported none
# (thoughts_token_count was None, total = prompt + candidates).
PRICE_PER_M_INPUT = 0.30
PRICE_PER_M_OUTPUT = 2.50


def post(query: str, user_id: str) -> int:
    body = json.dumps({"query": query, "user_id": user_id}).encode()
    req = urllib.request.Request(URL, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:   # 400 / 429 / 500 still have a status
        return exc.code


def main() -> None:
    # A fresh id per measurement, so this run's log lines can be picked out
    # from everything else in the file.
    user_id = f"cost_{time.strftime('%Y%m%d_%H%M%S')}"
    print(f"Measuring as user_id={user_id}, {len(QUERIES)} runs, "
          f"{PACE_S}s apart (about {len(QUERIES) * PACE_S // 60 + 1} min)\n")

    for i, q in enumerate(QUERIES, 1):
        started = time.monotonic()
        try:
            status = post(q, user_id)
        except urllib.error.URLError:
            sys.exit("Can't reach the server. Start it first: "
                     "$env:AI201_CACHE = '0'; python serve.py")
        print(f"  {i:2}. HTTP {status}  {q}")
        if i < len(QUERIES):
            time.sleep(max(0, PACE_S - (time.monotonic() - started)))

    runs = [e for e in read_entries() if e.get("user_id") == user_id]
    full = [e for e in runs if e["http_status"] == 200 and not e["stopped_early"]]

    print(f"\n{'#':>2}  {'item':<8} {'prompt':>6} {'output':>6} {'ms':>6}   cost ($)")
    for i, e in enumerate(runs, 1):
        cost = (e["prompt_tokens"] or 0) / 1e6 * PRICE_PER_M_INPUT \
             + (e["output_tokens"] or 0) / 1e6 * PRICE_PER_M_OUTPUT
        print(f"{i:>2}  {str(e['selected_item_id']):<8} {e['prompt_tokens']!s:>6} "
              f"{e['output_tokens']!s:>6} {e['duration_ms']:>6}   {cost:.6f}")

    if len(full) != len(QUERIES):
        print(f"\n⚠ Only {len(full)} of {len(QUERIES)} runs completed all three "
              "tools. Averages below are over those only.")
    if not full:
        sys.exit("No complete runs to average.")
    if any((e["prompt_tokens"] or 0) == 0 for e in full):
        print("\n⚠ Some complete runs logged 0 tokens: the cache is probably ON. "
              "Restart the server with $env:AI201_CACHE = '0'.")

    n = len(full)
    avg_in = sum(e["prompt_tokens"] for e in full) / n
    avg_out = sum(e["output_tokens"] for e in full) / n
    avg_ms = sum(e["duration_ms"] for e in full) / n
    cost_in = avg_in / 1e6 * PRICE_PER_M_INPUT
    cost_out = avg_out / 1e6 * PRICE_PER_M_OUTPUT
    per_run = cost_in + cost_out

    print(f"\nAverage over {n} complete runs:")
    print(f"  prompt tokens  {avg_in:8.1f}  × ${PRICE_PER_M_INPUT}/1M  = ${cost_in:.6f}")
    print(f"  output tokens  {avg_out:8.1f}  × ${PRICE_PER_M_OUTPUT}/1M  = ${cost_out:.6f}")
    print(f"  cost per run                              = ${per_run:.6f}")
    print(f"  time per run   {avg_ms:8.0f} ms")
    print("\nA hundred people a day, one run each:")
    print(f"  ${per_run:.6f} × 100            = ${per_run * 100:.4f} per day")
    print(f"  ${per_run * 100:.4f} × 30 days       = ${per_run * 3000:.2f} per month")
    print("Worst case, all 100 use their full daily limit "
          f"({config.HTTP_LIMIT_PER_DAY}/day):")
    print(f"  ${per_run:.6f} × 100 × {config.HTTP_LIMIT_PER_DAY}       "
          f"= ${per_run * 100 * config.HTTP_LIMIT_PER_DAY:.2f} per day")


if __name__ == "__main__":
    main()
