#!/usr/bin/env python3
"""
The capstone trials. ← UNIT 9

    (terminal 1)  $env:AI201_CACHE = '0'; python serve.py
    (terminal 2)  python capstone_eval.py --label before

Runs capstone criteria 1–4 (criteria.md, "# Capstone criteria") three times
each against the RUNNING server, the same way a user would, then scores every
one from logs/requests.jsonl and writes the run log to results/.

Criterion 5 (a fresh clone, following RUNNING.md) is a person following a
document, so it's run by hand; this script prints it as "manual".

Nothing about the server is changed between trials. Each criterion in each
trial uses its own user_id, so (a) its log lines can be picked out exactly,
and (b) one criterion's requests never count against another's rate limit.
"""

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

import config
from request_log import read_entries

BASE = "http://localhost:5000"

# The numbers in the criteria, so the score here can't drift from the text.
REFUSAL_MS = 500          # criterion 2: a 429 in under 500 ms
PRICE_IN = 0.30           # criterion 4: $ per 1M prompt tokens
PRICE_OUT = 2.50          # criterion 4: $ per 1M output tokens
COST_CEILING = 0.0016     # criterion 4: each complete run under $0.0016

# Criterion 1: three non-empty queries. Two that match and one that matches
# nothing, so both 200 paths (fit card, and stopped early) are covered.
C1_QUERIES = [
    "vintage graphic tee under $30",
    "leather belt",
    "designer ballgown size XXS under $5",
]

# Criterion 3: the three bad requests, exactly as criteria.md names them:
# a query with no characters, a query with only whitespace, and a query that
# is a number (not text).
C3_QUERIES = ["", "   ", 12345]

# Criterion 2: Bob uses up his 5-per-minute allowance with no-match queries
# (cheap: they stop before the model), then sends 3 more while Alice's real
# query is running the agent.
C2_FILLER = "designer ballgown size XXS under $5"
C2_ALICE = "vintage polo shirt"
C2_REFUSALS = 3
C2_START_DELAY_S = 0.5    # send Bob's 3 this long after Alice starts

# Criterion 4: three complete runs on three different items.
C4_QUERIES = ["denim jacket size M", "flannel shirt under $40", "bucket hat"]


# ── talking to the server ─────────────────────────────────────────────────────

def post(body) -> tuple[int, dict]:
    """POST a JSON body to /ask. Returns (http status, response JSON)."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{BASE}/ask", data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:      # 400 / 429 / 500 still answer
        return exc.code, json.loads(exc.read() or b"{}")


def lines_for(user_id: str) -> list[dict]:
    return [e for e in read_entries() if e.get("user_id") == user_id]


def cost_of(entry: dict) -> float:
    return ((entry.get("prompt_tokens") or 0) / 1e6 * PRICE_IN
            + (entry.get("output_tokens") or 0) / 1e6 * PRICE_OUT)


def ts(entry: dict) -> datetime:
    return datetime.fromisoformat(entry["timestamp"])


# ── the four criteria ─────────────────────────────────────────────────────────
# Each returns (passes, out_of, evidence lines, notes).

def criterion_1(uid: str):
    """3 of 3 non-empty queries each leave exactly one line with status 200."""
    statuses = {q: post({"query": q, "user_id": uid})[0] for q in C1_QUERIES}
    lines = lines_for(uid)
    passes, notes = 0, []
    for q in C1_QUERIES:
        mine = [e for e in lines if e["query"] == q]
        ok = statuses[q] == 200 and len(mine) == 1 and mine[0]["http_status"] == 200
        passes += ok
        if not ok:
            notes.append(f"{q!r}: response {statuses[q]}, {len(mine)} log line(s), "
                         f"logged status {[e['http_status'] for e in mine]}")
    return passes, len(C1_QUERIES), lines, notes


def criterion_2(uid_bob: str, uid_alice: str):
    """While Alice's run is going, Bob's 3 over-limit requests each get a 429
    in under 500 ms (duration_ms) with null tokens."""
    notes = []

    # Setup: Bob uses up his 5 for this minute.
    setup = [post({"query": C2_FILLER, "user_id": uid_bob})[0]
             for _ in range(config.HTTP_LIMIT_PER_MINUTE)]
    if setup != [200] * config.HTTP_LIMIT_PER_MINUTE:
        notes.append(f"setup: Bob's first {config.HTTP_LIMIT_PER_MINUTE} were {setup}, not all 200")

    # Alice's real query runs in the background and holds the lock.
    alice = threading.Thread(target=post, args=({"query": C2_ALICE, "user_id": uid_alice},))
    alice.start()
    time.sleep(C2_START_DELAY_S)
    refusal_statuses = [post({"query": C2_FILLER, "user_id": uid_bob})[0]
                        for _ in range(C2_REFUSALS)]
    alice.join()

    alice_lines = lines_for(uid_alice)
    bob_429s = [e for e in lines_for(uid_bob) if e["http_status"] == 429]
    if len(alice_lines) != 1:
        notes.append(f"Alice left {len(alice_lines)} log lines, expected 1")
        return 0, C2_REFUSALS, alice_lines + bob_429s, notes

    # Alice's line is written when her run ENDS; it started duration_ms earlier.
    a_end = ts(alice_lines[0])
    a_start = a_end - timedelta(milliseconds=alice_lines[0]["duration_ms"])

    passes = 0
    for i, e in enumerate(bob_429s, 1):
        overlapped = a_start <= ts(e) <= a_end
        fast = e["duration_ms"] < REFUSAL_MS
        no_tokens = e["prompt_tokens"] is None and e["output_tokens"] is None
        ok = overlapped and fast and no_tokens
        passes += ok
        if not ok:
            notes.append(f"refusal {i}: overlapped Alice's run={overlapped}, "
                         f"duration_ms={e['duration_ms']}, tokens="
                         f"{e['prompt_tokens']}/{e['output_tokens']}")
    if refusal_statuses != [429] * C2_REFUSALS:
        notes.append(f"Bob's {C2_REFUSALS} responses were {refusal_statuses}, not all 429")
    passes = min(passes, refusal_statuses.count(429))
    return passes, C2_REFUSALS, alice_lines + bob_429s, notes


def criterion_3(uid: str):
    """3 of 3 bad requests each get a 400 and leave exactly one line with 400."""
    statuses = [post({"query": q, "user_id": uid})[0] for q in C3_QUERIES]
    lines = lines_for(uid)
    passes, notes = 0, []
    for q, status in zip(C3_QUERIES, statuses):
        mine = [e for e in lines if e["query"] == q and type(e["query"]) is type(q)]
        ok = status == 400 and len(mine) == 1 and mine[0]["http_status"] == 400
        passes += ok
        if not ok:
            notes.append(f"{q!r}: response {status}, {len(mine)} log line(s), "
                         f"logged status {[e['http_status'] for e in mine]}")
    return passes, len(C3_QUERIES), lines, notes


def criterion_4(uid: str):
    """3 of 3 complete runs each cost under $0.0016 (cache off, default wardrobe)."""
    for q in C4_QUERIES:
        post({"query": q, "user_id": uid})        # no wardrobe → the default 10
    lines = lines_for(uid)
    passes, notes = 0, []
    for q in C4_QUERIES:
        mine = [e for e in lines if e["query"] == q]
        if len(mine) != 1:
            notes.append(f"{q!r}: {len(mine)} log lines, expected 1")
            continue
        e = mine[0]
        complete = e["http_status"] == 200 and e["stopped_early"] is False
        if (e["prompt_tokens"] or 0) == 0:
            notes.append(f"{q!r}: 0 prompt tokens. Is the cache on? (AI201_CACHE=0)")
        ok = complete and (e["prompt_tokens"] or 0) > 0 and cost_of(e) < COST_CEILING
        passes += ok
        notes.append(f"{q!r}: {e['prompt_tokens']} + {e['output_tokens']} tokens = "
                     f"${cost_of(e):.6f}{'' if ok else '  ← FAIL'}")
    return passes, len(C4_QUERIES), lines, notes


# ── running and writing it up ─────────────────────────────────────────────────

CRITERIA = [
    ("1. Successful responses logged", "3 of 3"),
    ("2. Refusals during another run: 429 < 500 ms, null tokens", "3 of 3"),
    ("3. Refused requests logged (400)", "3 of 3"),
    ("4. Cost per complete run < $0.0016", "3 of 3"),
    ("5. Starting FitFindr from RUNNING.md alone", "3 of 3"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="before", help="before / after")
    ap.add_argument("--trials", type=int, default=3)
    args = ap.parse_args()

    try:
        urllib.request.urlopen(f"{BASE}/health", timeout=5)
    except Exception:
        sys.exit("Can't reach the server. Start it first:\n"
                 "    $env:AI201_CACHE = '0'; python serve.py")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    results = []   # results[trial][criterion] = (passes, out_of, lines, notes)

    for t in range(1, args.trials + 1):
        print(f"\nTrial {t} of {args.trials}")
        uid = lambda c: f"{args.label}_t{t}_c{c}_{stamp}"   # noqa: E731
        trial = []
        for c, fn in enumerate([
            lambda: criterion_1(uid(1)),
            lambda: criterion_2(uid("2bob"), uid("2alice")),
            lambda: criterion_3(uid(3)),
            lambda: criterion_4(uid(4)),
        ], 1):
            r = fn()
            trial.append(r)
            print(f"  criterion {c}: {r[0]}/{r[1]}")
            for n in r[3]:
                print(f"      {n}")
        results.append(trial)

    # ── the run log, in the brief's format ──
    out = [f"# Capstone run log — {args.label}", "",
           f"`python capstone_eval.py --label {args.label}` on {time.strftime('%Y-%m-%d %H:%M')}, "
           "against `python serve.py` started with `AI201_CACHE=0` "
           "(criterion 4 flags any complete run with 0 tokens, which would mean it wasn't); "
           f"{args.trials} trials, nothing changed between them. "
           "Scored from logs/requests.jsonl.", "",
           "| Criterion | Target | " + " | ".join(f"Run {t}" for t in range(1, args.trials + 1))
           + " | Verdict |",
           "|---|---|" + "---|" * args.trials + "---|"]
    for c, (name, target) in enumerate(CRITERIA):
        if c == 4:
            out.append(f"| {name} | {target} | " + " | ".join("manual" for _ in results)
                       + " | see fresh-clone record |")
            continue
        cells = [f"{r[c][0]}/{r[c][1]}" for r in results]
        met = all(r[c][0] == r[c][1] for r in results)
        out.append(f"| {name} | {target} | " + " | ".join(cells)
                   + f" | {'MET' if met else 'MISSED'} |")

    for t, trial in enumerate(results, 1):
        out += ["", f"## Trial {t}"]
        for c, (passes, of, lines, notes) in enumerate(trial):
            out += ["", f"### {CRITERIA[c][0]} — {passes}/{of}"]
            out += [f"- {n}" for n in notes]
            out += ["", "```json"] + [json.dumps(e, ensure_ascii=False) for e in lines] + ["```"]

    config.RESULTS_DIR.mkdir(exist_ok=True)
    path = config.RESULTS_DIR / f"capstone_{args.label}_{stamp}.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\nWrote {path}")
    print("\n".join(out[4:4 + len(CRITERIA) + 2]))


if __name__ == "__main__":
    main()
